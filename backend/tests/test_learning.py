from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, func, event

from api.core.datetime_utils import utcnow
from api.models import Attempt, AttemptResult, Question, QuestionProgress, Image, QuestionImage, UserRole
from api.services.question_progress_service import question_progress_service as progress_service
from api.services.review_service import review_service
from api.services.attempt_service import attempt_service
from api.services.analytics_service import analytics_service
from api.schemas.attempt import AttemptCreate, AttemptUpdate
from api.schemas.question import QuestionCreate, QuestionUpdate
from api.services.question_service import question_service


@pytest.mark.parametrize('result, expected', [('CORRECT', 10), ('WRONG', 0), ('PARTIAL', 2), ('SKIPPED', 0)])
def test_zero_is_not_default_score(result, expected):
    progress = QuestionProgress(proficiency_score=0, consecutive_correct=0)
    assert progress_service._calculate_new_score(progress, Attempt(result=result)) == expected


def test_zero_score_review_priority():
    priority, _ = review_service._priority(QuestionProgress(proficiency_score=0, mastery_level=0))
    assert priority == 100


@pytest.mark.parametrize('endpoint', ['attempts', 'question-attempts', 'question-progress', 'review'])
@pytest.mark.parametrize('kind, expected', [('foreign', 403), ('deleted', 404), ('missing', 404)])
async def test_question_writes_require_access(db, users, client, endpoint, kind, expected):
    owner, other = users
    question = Question(user_id=other.id if kind == 'foreign' else owner.id, type='OTHER', is_deleted=kind == 'deleted')
    db.add(question)
    await db.commit()
    qid = str(uuid4() if kind == 'missing' else question.id)
    path = f'/api/v1/reviews/{qid}/complete' if endpoint == 'review' else '/api/v1/' + endpoint
    payload = {'result': 'WRONG', 'question_id': qid}
    response = await client.post(path, json=payload)
    assert response.status_code == expected, response.text
    assert (await db.scalar(select(func.count()).select_from(Attempt))) == 0
    assert (await db.scalar(select(func.count()).select_from(QuestionProgress))) == 0


@pytest.mark.parametrize('admin', [False, True])
async def test_owner_or_admin_can_record(db, users, client, admin):
    owner, other = users
    if admin:
        owner.role = UserRole.ADMIN
    question = Question(user_id=other.id if admin else owner.id, type='OTHER')
    db.add(question)
    await db.commit()
    response = await client.post('/api/v1/attempts', json={'question_id': str(question.id), 'result': 'CORRECT'})
    assert response.status_code == 201, response.text
    progress = (await db.execute(select(QuestionProgress))).scalar_one()
    assert progress.user_id == owner.id
    assert progress.total_attempts == 1 and progress.proficiency_score == 60


async def test_edit_delete_replays_progress_without_date_drift(db, users, client):
    owner, _ = users
    q = Question(user_id=owner.id, type='OTHER')
    db.add(q)
    await db.commit()
    at = utcnow() - timedelta(days=10)
    first = await attempt_service.create_attempt(db, owner.id, AttemptCreate(question_id=q.id, result='CORRECT', submitted_at=at))
    second = await attempt_service.create_attempt(db, owner.id, AttemptCreate(question_id=q.id, result='WRONG', submitted_at=at + timedelta(days=1)))
    progress = (await db.execute(select(QuestionProgress))).scalar_one()
    assert (progress.total_attempts, progress.proficiency_score) == (2, 45)
    due = progress.next_review_at
    await attempt_service.update_attempt(db, second.id, AttemptUpdate(note='note only'), owner.id)
    assert progress.next_review_at == due
    await attempt_service.update_attempt(db, second.id, AttemptUpdate(result='CORRECT'), owner.id)
    assert (progress.correct_attempts, progress.wrong_attempts, progress.proficiency_score) == (2, 0, 75)
    response = await client.delete('/api/v1/attempts/' + str(first.id))
    assert response.status_code == 204
    await db.refresh(progress)
    assert (progress.total_attempts, progress.correct_attempts, progress.proficiency_score) == (1, 1, 60)


async def test_backdated_attempt_and_recalculation(db, users):
    owner, _ = users
    q = Question(user_id=owner.id, type='OTHER')
    db.add(q)
    await db.commit()
    at = utcnow()
    await attempt_service.create_attempt(db, owner.id, AttemptCreate(question_id=q.id, result='CORRECT', submitted_at=at))
    await attempt_service.create_attempt(db, owner.id, AttemptCreate(question_id=q.id, result='WRONG', submitted_at=at-timedelta(days=1)))
    progress = (await db.execute(select(QuestionProgress))).scalar_one()
    assert progress.last_result == 'CORRECT'
    progress.proficiency_score = 99
    progress.self_assessment = 'needs practice'
    await db.commit()
    assert await review_service.recalculate(db, owner.id) == 1
    assert progress.proficiency_score == 45 and progress.self_assessment == 'needs practice'


@pytest.mark.parametrize('page_size', [1, 20, 100])
async def test_list_has_constant_query_count(db, users, client, page_size):
    owner, other = users
    questions = [Question(user_id=owner.id, type='OTHER') for _ in range(25)]
    db.add_all(questions)
    await db.flush()
    image = Image(user_id=owner.id, object_key='sample', sha256='0'*64, mime='image/png', size_bytes=10)
    db.add(image)
    await db.flush()
    for q in questions:
        db.add(QuestionImage(question_id=q.id, image_id=image.id, order_index=0))
        db.add(QuestionProgress(user_id=owner.id, question_id=q.id, proficiency_score=37))
        db.add(QuestionProgress(user_id=other.id, question_id=q.id, proficiency_score=99))
    await db.commit()
    selects = []
    engine = db.bind.sync_engine
    def count(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith('SELECT'):
            selects.append(statement)
    event.listen(engine, 'before_cursor_execute', count)
    try:
        response = await client.get(f'/api/v1/questions?page_size={page_size}')
    finally:
        event.remove(engine, 'before_cursor_execute', count)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['total'] == 25 and len(data['items']) == min(page_size, 25)
    assert all(q['proficiency_score'] == 37 and len(q['stem_images']) == 1 for q in data['items'])
    assert len(selects) == 4, selects


async def test_mastery_filtered_before_pagination(db, users, client):
    owner, other = users
    created = utcnow()
    questions = [Question(user_id=owner.id, type='OTHER', created_at=created) for _ in range(25)]
    db.add_all(questions)
    await db.flush()
    for index, q in enumerate(questions):
        db.add(QuestionProgress(user_id=owner.id, question_id=q.id, proficiency_score=90 if index < 7 else 40))
    db.add(Question(user_id=other.id, type='OTHER'))
    db.add(Question(user_id=owner.id, type='OTHER', is_deleted=True))
    await db.commit()
    ids = []
    for page in range(1, 4):
        data = (await client.get(f'/api/v1/questions?proficiency_min=81&page_size=3&page={page}')).json()
        assert data['total'] == 7 and data['total_pages'] == 3
        ids.extend(item['id'] for item in data['items'])
    assert len(set(ids)) == 7
    assert ids == [str(q.id) for q in sorted(questions[:7], key=lambda q: q.id, reverse=True)]


async def test_zero_filter_includes_unpracticed(db, users, client):
    owner, other = users
    q = Question(user_id=owner.id, type='OTHER')
    db.add(q)
    await db.flush()
    db.add(QuestionProgress(user_id=other.id, question_id=q.id, proficiency_score=99))
    await db.commit()
    data = (await client.get('/api/v1/questions?proficiency_max=0')).json()
    assert data['total'] == 1 and data['items'][0]['proficiency_score'] == 0


@pytest.mark.parametrize('query', ['proficiency_min=-1', 'proficiency_max=101', 'proficiency_min=invalid'])
async def test_filter_bounds(client, query):
    assert (await client.get('/api/v1/questions?' + query)).status_code == 422


async def test_deleted_questions_excluded_from_all_statistics(db, users, client):
    owner, _ = users
    q = Question(user_id=owner.id, type='OTHER', is_deleted=True)
    db.add(q)
    await db.flush()
    db.add(Attempt(user_id=owner.id, question_id=q.id, result='WRONG', error_tags_json=['KNOWLEDGE']))
    db.add(QuestionProgress(user_id=owner.id, question_id=q.id, is_mastered=True, next_review_at=utcnow()-timedelta(days=2)))
    await db.commit()
    overview = await analytics_service.overview(db, owner.id)
    assert all(value == 0 for value in overview.values())
    assert (await analytics_service.error_tags(db, owner.id))['items'] == []
    assert (await analytics_service.mastery_distribution(db, owner.id))['items'] == []
    assert all(value == 0 for value in (await attempt_service.get_attempt_stats(db, owner.id)).values())
    assert (await client.get('/api/v1/question-progress')).json()['total'] == 0
    assert (await client.get('/api/v1/reviews/today')).json()['items'] == []


@pytest.mark.parametrize('operation', ['create', 'update', 'attach', 'answer'])
async def test_foreign_images_rejected(db, users, client, operation):
    owner, other = users
    q = Question(user_id=owner.id, type='OTHER')
    image = Image(user_id=other.id, object_key='foreign', sha256='0'*64, mime='image/png', size_bytes=10)
    db.add_all([q, image])
    await db.commit()
    if operation == 'create':
        r = await client.post('/api/v1/questions', json={'type':'OTHER', 'stem_image_ids':[str(image.id)]})
    elif operation == 'update':
        r = await client.patch(f'/api/v1/questions/{q.id}', json={'stem_image_ids':[str(image.id)]})
    elif operation == 'attach':
        r = await client.post(f'/api/v1/questions/{q.id}/images?image_id={image.id}')
    else:
        r = await client.put(f'/api/v1/questions/{q.id}/answer', json={'answer_type':'TEXT', 'images':[{'image_id':str(image.id), 'order_index':0}]})
    assert r.status_code == 403, r.text
    assert (await db.scalar(select(func.count()).select_from(QuestionImage))) == 0


async def test_question_creation_rolls_back_images_on_failure(db, users, monkeypatch):
    owner, _ = users
    image = Image(user_id=owner.id, object_key='own', sha256='0'*64, mime='image/png', size_bytes=10)
    db.add(image)
    await db.commit()
    async def fail(*args, **kwargs):
        raise RuntimeError('simulated link failure')
    monkeypatch.setattr(question_service, '_update_question_images', fail)
    with pytest.raises(RuntimeError):
        await question_service.create_question(db, owner.id, QuestionCreate(type='OTHER', stem_image_ids=[image.id]))
    await db.rollback()
    assert await db.scalar(select(func.count()).select_from(Question)) == 0
