from datetime import date, timedelta
from importlib import import_module

import pytest
from sqlalchemy import event, select, func

from api.core.datetime_utils import local_day_bounds_utc
from api.models import Question, QuestionProgress, PaperSet, PaperSetItem, Image, QuestionImage, Answer, AnswerImage
from api.models.user import UserRole


@pytest.fixture
def review_day(monkeypatch):
    day = date(2026, 10, 22)
    for module in ['api.api.v1.reviews', 'api.services.review_service']:
        monkeypatch.setattr(import_module(module), 'local_date', lambda: day)
    return day


async def seed_due(db, user_id, day, count, subject='数学'):
    start, _ = local_day_bounds_utc(day)
    questions = [Question(user_id=user_id, type='OTHER', subject=subject, stem_text=f'题干 {i}') for i in range(count)]
    db.add_all(questions)
    await db.flush()
    progress = [QuestionProgress(user_id=user_id, question_id=q.id, next_review_at=start,
                                 proficiency_score=i % 5) for i, q in enumerate(questions)]
    db.add_all(progress)
    await db.commit()
    return questions, progress


async def test_review_pagination_is_complete_and_stable(db, users, client, review_day):
    questions, progress = await seed_due(db, users[0].id, review_day, 105)
    first = (await client.get('/api/v1/reviews/today')).json()
    second = (await client.get('/api/v1/reviews/today?page=2')).json()
    assert (first['total'], first['page_size'], first['total_pages']) == (105, 100, 2)
    ids = [item['question_id'] for item in first['items'] + second['items']]
    expected = [str(p.question_id) for p in sorted(progress, key=lambda p: (p.proficiency_score, str(p.id)))]
    assert ids == expected and len(set(ids)) == len(questions)
    assert first == (await client.get('/api/v1/reviews/today')).json()
    assert all(item['question'] is None and item['answer'] is None for item in first['items'])
    assert (await client.get('/api/v1/reviews/today?page=3')).json()['items'] == []


async def test_review_day_boundary_subject_and_access(db, users, client, review_day):
    owner, other = users
    _, end = local_day_bounds_utc(review_day)
    questions = [Question(user_id=owner.id, type='OTHER', subject='数学'),
                 Question(user_id=owner.id, type='OTHER', subject='物理'),
                 Question(user_id=owner.id, type='OTHER', subject='将来'),
                 Question(user_id=owner.id, type='OTHER', subject='未安排'),
                 Question(user_id=owner.id, type='OTHER', subject='已删除', is_deleted=True),
                 Question(user_id=other.id, type='OTHER', subject='其他账号')]
    db.add_all(questions)
    await db.flush()
    for index, q in enumerate(questions):
        due = None if index == 3 else end + timedelta(microseconds=1) if index == 2 else end
        # Even stale own progress must not grant access to a foreign question.
        db.add(QuestionProgress(user_id=owner.id, question_id=q.id, next_review_at=due))
    db.add(QuestionProgress(user_id=other.id, question_id=questions[0].id, next_review_at=end, proficiency_score=99))
    await db.commit()
    result = (await client.get('/api/v1/reviews/today?include_details=true')).json()
    assert result['total'] == 2 and result['subjects'] == ['数学', '物理']
    assert {item['question_id'] for item in result['items']} == {str(q.id) for q in questions[:2]}
    assert all(item['proficiency_score'] == 50 for item in result['items'])
    result = (await client.get('/api/v1/reviews/today', params={'subject': '数学'})).json()
    assert result['total'] == 1 and result['subjects'] == ['数学', '物理']
    assert (await client.get('/api/v1/reviews/queue')).json()['total'] == 4
    owner.role = UserRole.ADMIN
    result = (await client.get('/api/v1/reviews/today?include_details=true')).json()
    assert result['total'] == 3
    assert all(item['proficiency_score'] == 50 for item in result['items'])


@pytest.mark.parametrize('count', [1, 25, 100])
async def test_review_details_use_fixed_queries_and_include_images(db, users, client, review_day, count):
    questions, _ = await seed_due(db, users[0].id, review_day, count)
    image = Image(user_id=users[0].id, object_key='review-image', sha256='0' * 64, mime='image/png', size_bytes=10)
    db.add(image)
    await db.flush()
    for q in questions:
        db.add_all([Answer(question_id=q.id, answer_type='LATEX', answer_latex=r'$x=1$', explanation_text='解析'),
                    QuestionImage(question_id=q.id, image_id=image.id, order_index=0),
                    AnswerImage(question_id=q.id, image_id=image.id, order_index=0)])
    await db.commit()
    selects = []
    def count_selects(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith('SELECT'):
            selects.append(statement)
    engine = db.bind.sync_engine
    event.listen(engine, 'before_cursor_execute', count_selects)
    try:
        response = await client.get('/api/v1/reviews/today?include_details=true', headers={'Authorization': 'Bearer test-image-token'})
    finally:
        event.remove(engine, 'before_cursor_execute', count_selects)
    assert response.status_code == 200, response.text
    assert len(selects) == 6, selects
    assert len(response.json()['items']) == count
    for item in response.json()['items']:
        assert item['question']['stem_text'].startswith('题干')
        assert item['answer']['answer_latex'] == r'$x=1$'
        assert item['answer']['explanation_text'] == '解析'
        for images in [item['question']['stem_images'], item['answer']['images']]:
            assert images[0]['url'] == f'http://test/api/v1/images/{image.id}/file?token=test-image-token'


@pytest.mark.parametrize('query', ['page=0', 'page_size=0', 'page_size=101', 'subject=', 'subject=' + 'x' * 65])
async def test_invalid_review_filters(client, query):
    assert (await client.get('/api/v1/reviews/today?' + query)).status_code == 422


async def test_daily_set_uses_all_pages_reuses_safely_and_preserves_item_metadata(db, users, client, review_day):
    owner, other = users
    questions, progress = await seed_due(db, owner.id, review_day, 105)
    foreign, _ = await seed_due(db, other.id, review_day, 1)
    manual = PaperSet(user_id=owner.id, title=f'复习-{review_day}')
    other_set = PaperSet(user_id=other.id, title=f'复习-{review_day}',
                         render_options={'daily_review_key': f'{review_day}:'})
    db.add_all([manual, other_set])
    await db.flush()
    db.add(PaperSetItem(paper_set_id=other_set.id, question_id=foreign[0].id, order_index=1))
    await db.commit()
    response = await client.post('/api/v1/reviews/daily-paper-set', json={})
    assert response.status_code == 200, response.text
    first = response.json()
    assert first['item_count'] == 105 and first['reused'] is False
    assert first['paper_set_id'] != str(manual.id)
    set_id = next(x.id for x in (await db.execute(select(PaperSet))).scalars() if str(x.id) == first['paper_set_id'])
    items = (await db.execute(select(PaperSetItem).where(PaperSetItem.paper_set_id == set_id))).scalars().all()
    assert len(items) == 105 and foreign[0].id not in {item.question_id for item in items}
    # Rename the generated set: its identity must not depend on its title.
    generated = await db.get(PaperSet, set_id)
    generated.title = '我的复习卷'
    retained = next(item for item in items if item.question_id == questions[1].id)
    retained.score, retained.section_title = 12, '保留分组'
    progress[0].next_review_at = local_day_bounds_utc(review_day)[1] + timedelta(days=1)
    await db.commit()
    second = (await client.post('/api/v1/reviews/daily-paper-set', json={})).json()
    assert second['paper_set_id'] == first['paper_set_id'] and second['reused'] is True
    assert second['title'] == '我的复习卷' and second['item_count'] == 104
    items = (await db.execute(select(PaperSetItem).where(PaperSetItem.paper_set_id == set_id))).scalars().all()
    assert questions[0].id not in {item.question_id for item in items}
    assert sorted(item.order_index for item in items) == list(range(1, 105))
    await db.refresh(retained)
    assert retained.score == 12 and retained.section_title == '保留分组'
    assert (await db.get(PaperSet, manual.id)).title == f'复习-{review_day}'
    assert await db.scalar(select(func.count()).select_from(PaperSetItem)
                           .where(PaperSetItem.paper_set_id == other_set.id)) == 1


async def test_daily_set_filter_and_no_due_questions(db, users, client, review_day):
    math, _ = await seed_due(db, users[0].id, review_day, 2)
    await seed_due(db, users[0].id, review_day, 3, subject='物理')
    response = await client.post('/api/v1/reviews/daily-paper-set', json={'subject': '数学'})
    assert response.status_code == 200, response.text
    assert response.json()['item_count'] == len(math)
    all_subjects = (await client.post('/api/v1/reviews/daily-paper-set', json={})).json()
    assert all_subjects['item_count'] == 5 and all_subjects['paper_set_id'] != response.json()['paper_set_id']
    response = await client.post('/api/v1/reviews/daily-paper-set', json={'subject': '不存在'})
    assert response.status_code == 400
    assert await db.scalar(select(func.count()).select_from(PaperSet)) == 2


@pytest.mark.parametrize('reuse', [False, True])
async def test_daily_set_failure_rolls_back_entire_update(db, users, client, review_day, monkeypatch, reuse):
    questions, progress = await seed_due(db, users[0].id, review_day, 2)
    original_set_id = None
    if reuse:
        await client.post('/api/v1/reviews/daily-paper-set', json={})
        original_set_id = await db.scalar(select(PaperSet.id))
        progress[0].next_review_at = local_day_bounds_utc(review_day)[1] + timedelta(days=1)
        await db.commit()
    async def fail_after_flush():
        await db.flush()
        raise RuntimeError('simulated write failure')
    with monkeypatch.context() as patch:
        patch.setattr(db, 'commit', fail_after_flush)
        with pytest.raises(RuntimeError, match='simulated write failure'):
            await client.post('/api/v1/reviews/daily-paper-set', json={})
    assert await db.scalar(select(func.count()).select_from(PaperSet)) == int(reuse)
    if reuse:
        items = (await db.execute(select(PaperSetItem).where(PaperSetItem.paper_set_id == original_set_id))).scalars().all()
        assert len(items) == 2 and sorted(item.order_index for item in items) == [1, 2]
