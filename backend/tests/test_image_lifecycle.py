import io
from datetime import timedelta
from uuid import uuid4

import pytest
from PIL import Image as PillowImage
from sqlalchemy import func, select

from api.core.config import settings
from api.core.datetime_utils import utcnow
from api.core.jobs import fetch_next_job, recover_stale_jobs
from api.models import Image, Question, QuestionImage, AnswerImage, QuestionExtraction, ExtractionImage, Job, JobType
from api.services.image_service import image_service
from api.worker import ExportWorker, SUPPORTED_JOB_TYPES


def png(size=(4, 3)):
    buffer = io.BytesIO()
    PillowImage.new('RGB', size, 'white').save(buffer, format='PNG')
    return buffer.getvalue()


class Storage:
    def __init__(self):
        self.objects = {}
        self.deleted = []
        self.reads = []

    def put_object(self, Bucket, Key, Body, ContentType):
        self.objects[Key] = (Body, ContentType)

    def get_object(self, Bucket, Key):
        self.reads.append(Key)
        data, mime = self.objects[Key]
        return {'Body': io.BytesIO(data), 'ContentLength': len(data), 'ContentType': mime}

    def delete_object(self, Bucket, Key):
        self.deleted.append(Key)
        self.objects.pop(Key, None)


@pytest.fixture
def storage(monkeypatch):
    storage = Storage()
    monkeypatch.setattr(image_service, '_s3_client', storage)
    return storage


async def test_upload_derives_metadata_from_bytes(db, users, client, storage):
    data = png()
    response = await client.post('/api/v1/images/upload', files={'file': ('fake.jpg', data, 'image/jpeg')})
    assert response.status_code == 201, response.text
    result = response.json()
    assert (result['mime'], result['width'], result['height'], result['size_bytes']) == ('image/png', 4, 3, len(data))
    assert result['object_key'].endswith('.png')
    assert storage.objects[result['object_key']] == (data, 'image/png')


async def test_signed_upload_binds_size_and_rejects_oversized_request(users, client, storage, monkeypatch):
    captured = []
    def sign(operation, Params, ExpiresIn):
        captured.append(Params)
        return 'https://storage.invalid/signed-upload'
    monkeypatch.setattr(storage, 'generate_presigned_url', sign, raising=False)
    payload = {'filename': 'photo.png', 'content_type': 'image/png', 'size_bytes': 123}
    response = await client.post('/api/v1/images/upload-url', json=payload)
    assert response.status_code == 200, response.text
    assert captured[0]['ContentLength'] == 123
    assert captured[0]['Key'].startswith(f'uploads/{users[0].id}/')
    payload['size_bytes'] = settings.IMAGE_MAX_UPLOAD_BYTES + 1
    assert (await client.post('/api/v1/images/upload-url', json=payload)).status_code == 400
    assert len(captured) == 1


@pytest.mark.parametrize('kind', ['empty', 'fake', 'svg', 'truncated', 'bytes', 'pixels', 'animation'])
async def test_invalid_upload_never_reaches_storage(db, users, client, storage, monkeypatch, kind):
    data = png()
    if kind == 'empty':
        data = b''
    elif kind == 'fake':
        data = b'not an image'
    elif kind == 'svg':
        data = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    elif kind == 'truncated':
        data = data[:45]
    elif kind == 'bytes':
        monkeypatch.setattr(settings, 'IMAGE_MAX_UPLOAD_BYTES', 30)
    elif kind == 'pixels':
        monkeypatch.setattr(settings, 'IMAGE_MAX_PIXELS', 11)
    else:
        stream = io.BytesIO()
        PillowImage.new('RGB', (2, 2), 'white').save(stream, format='GIF', save_all=True,
            append_images=[PillowImage.new('RGB', (2, 2), 'black')])
        data = stream.getvalue()
    response = await client.post('/api/v1/images/upload', files={'file': ('image.png', data, 'image/png')})
    assert response.status_code == 400, response.text
    assert not storage.objects
    assert await db.scalar(select(func.count()).select_from(Image)) == 0


async def test_registration_copies_validated_staging_bytes_and_ignores_claimed_metadata(db, users, client, storage):
    key = f'uploads/{users[0].id}/{uuid4().hex}_photo.png'
    storage.objects[key] = (png(), 'text/html')
    response = await client.post('/api/v1/images', json={
        'object_key': key, 'mime': 'text/html', 'size_bytes': 999, 'sha256': 'fake', 'width': 999,
        'storage_url': 'https://untrusted.invalid/image',
    })
    assert response.status_code == 201, response.text
    saved = response.json()
    assert saved['mime'] == 'image/png' and saved['width'] == 4 and saved['size_bytes'] == len(png())
    assert saved['object_key'] != key and 'untrusted' not in saved['storage_url']
    storage.objects[key] = (b'replaced through old signed URL', 'text/html')
    assert storage.objects[saved['object_key']][0] == png()
    cleanup = (await db.execute(select(Job))).scalar_one()
    assert cleanup.type == 'IMAGE_CLEANUP' and cleanup.payload['object_key'] == key


@pytest.mark.parametrize('kind', ['foreign', 'export', 'final'])
async def test_registration_rejects_keys_outside_own_staging(db, users, client, storage, kind):
    keys = {'foreign': f'uploads/{users[1].id}/{uuid4().hex}_photo.png',
            'export': f'exports/{uuid4()}/private.zip', 'final': f'images/{users[0].id}/{uuid4().hex}_image.png'}
    response = await client.post('/api/v1/images', json={'object_key': keys[kind]})
    assert response.status_code == 403, response.text
    assert storage.reads == []


async def test_registration_rechecks_size_limit(db, users, client, storage, monkeypatch):
    key = f'uploads/{users[0].id}/{uuid4().hex}_photo.png'
    storage.objects[key] = (png(), 'image/png')
    monkeypatch.setattr(settings, 'IMAGE_MAX_UPLOAD_BYTES', 30)
    response = await client.post('/api/v1/images', json={'object_key': key})
    assert response.status_code == 400
    assert await db.scalar(select(func.count()).select_from(Image)) == 0


async def seed_image(db, user_id):
    image = Image(user_id=user_id, object_key=f'images/{user_id}/{uuid4().hex}.png',
                  sha256='0' * 64, mime='image/png', size_bytes=12)
    db.add(image)
    await db.commit()
    return image


@pytest.mark.parametrize('link_type', ['question', 'answer', 'extraction'])
async def test_referenced_image_cannot_be_deleted(db, users, client, storage, link_type):
    image = await seed_image(db, users[0].id)
    if link_type == 'extraction':
        parent = QuestionExtraction(user_id=users[0].id)
        db.add(parent)
        await db.flush()
        db.add(ExtractionImage(extraction_id=parent.id, image_id=image.id, order_index=0))
    else:
        parent = Question(user_id=users[0].id, type='OTHER')
        db.add(parent)
        await db.flush()
        model = QuestionImage if link_type == 'question' else AnswerImage
        db.add(model(question_id=parent.id, image_id=image.id, order_index=0))
    await db.commit()
    response = await client.delete(f'/api/v1/images/{image.id}')
    assert response.status_code == 409, response.text
    assert storage.deleted == []
    assert await db.scalar(select(func.count()).select_from(Image)) == 1
    assert await db.scalar(select(func.count()).select_from(Job)) == 0


async def test_cleanup_is_queued_only_after_database_commit(db, users, client, storage, monkeypatch):
    image = await seed_image(db, users[0].id)
    image_id = image.id
    async def fail_after_flush():
        await db.flush()
        raise RuntimeError('database commit failed')
    with monkeypatch.context() as patch:
        patch.setattr(db, 'commit', fail_after_flush)
        with pytest.raises(RuntimeError, match='database commit failed'):
            await client.delete(f'/api/v1/images/{image_id}')
    assert storage.deleted == []
    assert await db.get(Image, image_id) is not None
    assert await db.scalar(select(func.count()).select_from(Job)) == 0


async def test_storage_failure_retries_cleanup_without_losing_task(db, users, client, storage, monkeypatch):
    image = await seed_image(db, users[0].id)
    key = image.object_key
    response = await client.delete(f'/api/v1/images/{image.id}')
    assert response.status_code == 200 and storage.deleted == []
    assert await db.scalar(select(func.count()).select_from(Image)) == 0
    job = await fetch_next_job(db, 'cleaner', SUPPORTED_JOB_TYPES)
    job_id = job.id
    def fail(key):
        raise RuntimeError('storage unavailable')
    with monkeypatch.context() as patch:
        patch.setattr(image_service, 'delete_image_bytes', fail)
        await ExportWorker('cleaner').process_job(db, job)
    await db.refresh(job)
    assert job.status == 'PENDING' and job.last_error
    job.run_after = utcnow() - timedelta(seconds=1)
    await db.commit()
    retry = await fetch_next_job(db, 'cleaner', SUPPORTED_JOB_TYPES)
    assert retry.id == job_id
    await ExportWorker('cleaner').process_job(db, retry)
    assert retry.status == 'DONE' and retry.attempts == 2
    assert storage.deleted == [key]


async def test_interrupted_cleanup_can_safely_resume(db, users):
    job = Job(user_id=users[0].id, type=JobType.IMAGE_CLEANUP.value, payload={'object_key': 'unused.png'},
              status='RUNNING', locked_by='dead-worker', locked_at=utcnow() - timedelta(days=1))
    db.add(job)
    await db.commit()
    assert await recover_stale_jobs(db) == 1
    assert job.status == 'PENDING' and job.locked_by is None
