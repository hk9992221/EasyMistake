import json
from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select, func
from api.core.datetime_utils import utcnow
from api.core.deps import get_current_user
from api.core.jobs import fetch_next_job, recover_stale_jobs, heartbeat_job
from api.main import app
from api.models import (
    Job, JobType, QuestionExtraction, Image, Export, PaperSet, Question,
)
from api.models.grading_record import GradingRecord
from api.schemas.extraction import ExtractionCreate
from api.schemas.export import ExportCreate
from api.services.extraction_service import extraction_service
from api.services.export_service import export_service
from api.services.image_service import image_service
from api.services.ocr_service import ocr_service
from api.scripts.import_grading import import_records
from api.worker import ExportWorker, SUPPORTED_JOB_TYPES


async def create_extraction(db, user_id):
    image = Image(user_id=user_id, object_key=str(uuid4()), sha256='0'*64, mime='image/png', size_bytes=10)
    db.add(image)
    await db.commit()
    return await extraction_service.create_extraction(db, user_id, ExtractionCreate(image_ids=[image.id]))


@pytest.mark.parametrize('response, expected', [
    ({'problem':'What is 2 + 2?', 'number':'1'}, 'DONE'),
    ({'error':'upstream unavailable'}, 'FAILED'),
    ({'raw':'invalid response'}, 'FAILED'),
])
async def test_worker_consumes_ocr_and_records_terminal_status(db, users, monkeypatch, tmp_path, response, expected):
    extraction = await create_extraction(db, users[0].id)
    extraction_id = extraction.id
    monkeypatch.setattr(image_service, 'fetch_image_bytes', lambda key: b'image')
    recognize = AsyncMock(return_value=response.copy())
    monkeypatch.setattr(ocr_service, 'recognize', recognize)
    job = await fetch_next_job(db, 'test-worker', SUPPORTED_JOB_TYPES)
    job_id = job.id
    worker = ExportWorker('test-worker')
    worker.temp_dir = tmp_path
    await worker.process_job(db, job)
    extraction = await db.get(QuestionExtraction, extraction_id)
    job = await db.get(Job, job_id)
    assert extraction.status == job.status == expected
    assert job.locked_at is None and job.locked_by is None
    assert recognize.await_count == 1
    if expected == 'DONE':
        assert extraction.raw_json['questions'][0]['problem'] == 'What is 2 + 2?'
    else:
        assert extraction.error


async def test_duplicate_retry_reuses_active_job_without_calling_ocr(db, users, client, monkeypatch):
    extraction = await create_extraction(db, users[0].id)
    recognize = AsyncMock(side_effect=AssertionError('HTTP must not run OCR'))
    monkeypatch.setattr(ocr_service, 'recognize', recognize)
    for _ in range(2):
        response = await client.post(f'/api/v1/extractions/{extraction.id}/retry')
        assert response.status_code == 200, response.text
        assert response.json()['status'] == 'PENDING'
    assert await db.scalar(select(func.count()).select_from(Job)) == 1
    recognize.assert_not_called()


async def test_completed_extraction_does_not_call_ocr_again(db, users, monkeypatch):
    extraction = await create_extraction(db, users[0].id)
    extraction.status = 'DONE'
    await db.commit()
    recognize = AsyncMock(side_effect=AssertionError('completed task repeated'))
    monkeypatch.setattr(ocr_service, 'recognize', recognize)
    job = await fetch_next_job(db, 'test-worker', SUPPORTED_JOB_TYPES)
    await ExportWorker('test-worker').process_job(db, job)
    assert job.status == 'DONE'
    recognize.assert_not_called()


async def test_worker_interruption_is_visible_and_explicitly_retryable(db, users):
    extraction = await create_extraction(db, users[0].id)
    job = await fetch_next_job(db, 'dead-worker', SUPPORTED_JOB_TYPES)
    extraction.status = 'RUNNING'
    job.locked_at = utcnow() - timedelta(hours=1)
    await db.commit()
    assert await recover_stale_jobs(db) == 1
    assert extraction.status == job.status == 'FAILED'
    assert job.locked_at is None and job.locked_by is None
    assert not await heartbeat_job(db, job.id, 'dead-worker')
    # No automatic repeat of an OCR request whose provider may already have billed it.
    assert await fetch_next_job(db, 'new-worker', SUPPORTED_JOB_TYPES) is None
    await extraction_service.retry_extraction(db, extraction)
    new_job = await fetch_next_job(db, 'new-worker', SUPPORTED_JOB_TYPES)
    assert new_job.id != job.id and extraction.status == 'PENDING'


@pytest.mark.parametrize('kind', ['extraction', 'export'])
async def test_resource_and_job_created_in_one_transaction(db, users, monkeypatch, kind):
    user_id = users[0].id
    async def fail(*args, **kwargs):
        raise RuntimeError('queue write failed')
    if kind == 'extraction':
        image = Image(user_id=user_id, object_key='atomic', sha256='0'*64, mime='image/png', size_bytes=10)
        db.add(image)
        await db.commit()
        monkeypatch.setattr('api.services.extraction_service.create_job', fail)
        payload = ExtractionCreate(image_ids=[image.id])
        invoke = lambda: extraction_service.create_extraction(db, user_id, payload)
        model = QuestionExtraction
    else:
        paper = PaperSet(user_id=user_id, title='test')
        db.add(paper)
        await db.commit()
        monkeypatch.setattr('api.services.export_service.create_job', fail)
        payload = ExportCreate(paper_set_id=paper.id, format='MARKDOWN_ZIP')
        invoke = lambda: export_service.create_export(db, user_id, payload)
        model = Export
    with pytest.raises(RuntimeError):
        await invoke()
    await db.rollback()
    assert await db.scalar(select(func.count()).select_from(model)) == 0
    assert await db.scalar(select(func.count()).select_from(Job)) == 0


@pytest.mark.parametrize('uploaded, expected', [(True, 'DONE'), (False, 'FAILED')])
async def test_export_worker_finishes_resource_and_job_together(db, users, monkeypatch, tmp_path, uploaded, expected):
    from api.core.s3 import s3_client
    paper = PaperSet(user_id=users[0].id, title='test')
    db.add(paper)
    await db.commit()
    export = await export_service.create_export(db, users[0].id, ExportCreate(paper_set_id=paper.id, format='MARKDOWN_ZIP'))
    export_id = export.id
    worker = ExportWorker('test-worker')
    worker.temp_dir = tmp_path
    async def generate(*args):
        path = tmp_path / 'result.zip'
        path.write_bytes(b'archive')
        return path, 7, '0'*64
    monkeypatch.setattr(worker, '_generate_export', generate)
    monkeypatch.setattr(s3_client, 'upload_file', lambda *args, **kwargs: uploaded)
    job = await fetch_next_job(db, 'test-worker', SUPPORTED_JOB_TYPES)
    job_id = job.id
    await worker.process_job(db, job)
    export, job = await db.get(Export, export_id), await db.get(Job, job_id)
    assert export.status == job.status == expected
    assert export.finished_at is not None
    assert job.locked_at is None and job.locked_by is None


async def test_grading_requires_authentication_and_separates_accounts(db, users, client):
    owner, other = users
    other_id = other.id
    del app.dependency_overrides[get_current_user]
    assert (await client.get('/api/v1/grading/records')).status_code == 401
    assert (await client.post('/api/v1/grading/records', json={})).status_code == 401
    app.dependency_overrides[get_current_user] = lambda: owner
    payload = {'student_name':'Student', 'paper_name':'Quiz', 'score':90}
    assert (await client.post('/api/v1/grading/records', json=payload)).status_code == 201
    assert len((await client.get('/api/v1/grading/records')).json()['records']) == 1
    app.dependency_overrides[get_current_user] = lambda: other
    assert (await client.get('/api/v1/grading/records')).json()['records'] == []
    await client.post('/api/v1/grading/records', json=payload)
    assert (await db.scalar(select(func.count()).select_from(GradingRecord).where(GradingRecord.user_id == other_id))) == 1


async def test_legacy_grading_import_is_idempotent_and_preserves_file(db, users, tmp_path):
    owner, other = users
    path = tmp_path / 'records.json'
    contents = json.dumps([{'id':'old-1', 'created_at':'2026-03-01 12:00:00', 'student_name':'Student', 'paper_name':'Quiz', 'score':90}])
    path.write_text(contents)
    assert await import_records(db, path, owner.email) == 1
    assert await import_records(db, path, owner.email) == 0
    with pytest.raises(ValueError, match='another account'):
        await import_records(db, path, other.email)
    assert path.read_text() == contents


async def test_bulk_confirmation_rolls_back_on_invalid_question(db, users, client):
    extraction = await create_extraction(db, users[0].id)
    response = await client.post(f'/api/v1/extractions/{extraction.id}/questions', json=[
        {'type':'OTHER', 'stem_text':'first question'},
        {'type':'OTHER', 'stem_image_ids':[str(uuid4())]},
    ])
    assert response.status_code == 404, response.text
    assert await db.scalar(select(func.count()).select_from(Question)) == 0
