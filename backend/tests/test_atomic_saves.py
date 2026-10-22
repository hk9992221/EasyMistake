from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, func, select

from api.core.deps import get_current_user
from api.main import app
from api.models import Answer, AnswerImage, Image, PaperSet, PaperSetItem, Question, QuestionImage


async def seed_images(db, user_id):
    images = [Image(user_id=user_id, object_key=f'{uuid4()}.png', sha256='0' * 64,
                    mime='image/png', size_bytes=8) for _ in range(2)]
    db.add_all(images)
    await db.commit()
    return images


def bundle(images=()):
    return {
        'request_id': str(uuid4()),
        'question': {'type': 'OTHER', 'subject': '数学', 'stem_text': '1 + 1 = ?',
                     'stem_image_ids': [str(images[0].id)] if images else []},
        'answer': {'answer_type': 'MIXED' if images else 'TEXT', 'answer_text': '2',
                   'images': [{'image_id': str(images[1].id), 'order_index': 0}] if images else []},
    }


async def test_complete_save_and_lost_response_retry(db, users, client):
    images = await seed_images(db, users[0].id)
    payload = bundle(images)
    first = await client.post('/api/v1/questions/with-answer', json=payload)
    assert first.status_code == 201, first.text
    qid = UUID(first.json()['id'])
    # Simulate the client losing the first successful response and retrying.
    again = await client.post('/api/v1/questions/with-answer', json=payload)
    assert again.status_code == 201 and again.json()['id'] == str(qid)
    assert first.json()['stem_images'][0]['image_id'] == str(images[0].id)
    assert 'client_payload_hash' not in first.json()
    for model in (Question, Answer, QuestionImage, AnswerImage):
        assert await db.scalar(select(func.count()).select_from(model)) == 1
    answer = (await db.execute(select(Answer).where(Answer.question_id == qid))).scalar_one()
    assert answer.answer_text == '2' and answer.answer_type == 'MIXED'
    link = (await db.execute(select(AnswerImage))).scalar_one()
    assert link.image_id == images[1].id and link.order_index == 0


async def test_request_id_is_scoped_to_account(db, users, client):
    payload = bundle()
    first = await client.post('/api/v1/questions/with-answer', json=payload)
    app.dependency_overrides[get_current_user] = lambda: users[1]
    second = await client.post('/api/v1/questions/with-answer', json=payload)
    assert first.status_code == second.status_code == 201
    assert first.json()['id'] != second.json()['id']
    assert await db.scalar(select(func.count()).select_from(Question)) == 2


@pytest.mark.parametrize('change', ['content', 'deleted'])
async def test_request_id_conflict_does_not_overwrite_or_resurrect(db, users, client, change):
    payload = bundle()
    first = await client.post('/api/v1/questions/with-answer', json=payload)
    qid = UUID(first.json()['id'])
    if change == 'content':
        payload['answer']['answer_text'] = 'changed'
    else:
        await client.delete(f'/api/v1/questions/{qid}')
    response = await client.post('/api/v1/questions/with-answer', json=payload)
    assert response.status_code == 409, response.text
    assert await db.scalar(select(func.count()).select_from(Question)) == 1
    question = await db.get(Question, qid)
    assert question.is_deleted == (change == 'deleted')
    assert await db.scalar(select(Answer.answer_text).where(Answer.question_id == qid)) == '2'


@pytest.mark.parametrize('location', ['stem', 'answer'])
@pytest.mark.parametrize('kind, status', [('foreign', 403), ('missing', 404)])
async def test_complete_save_checks_all_image_access(db, users, client, location, kind, status):
    images = await seed_images(db, users[0].id)
    foreign = await seed_images(db, users[1].id)
    payload = bundle(images)
    image_id = str(foreign[0].id if kind == 'foreign' else uuid4())
    if location == 'stem':
        payload['question']['stem_image_ids'].append(image_id)
    else:
        payload['answer']['images'].append({'image_id': image_id, 'order_index': 1})
    response = await client.post('/api/v1/questions/with-answer', json=payload)
    assert response.status_code == status, response.text
    for model in (Question, Answer, QuestionImage, AnswerImage):
        assert await db.scalar(select(func.count()).select_from(model)) == 0


async def test_complete_save_failure_rolls_back_all_parts_and_allows_retry(db, users, client, monkeypatch):
    images = await seed_images(db, users[0].id)
    payload = bundle(images)

    async def fail_after_flush():
        await db.flush()
        # All four parts reached the transaction before the injected failure.
        for model in (Question, Answer, QuestionImage, AnswerImage):
            assert await db.scalar(select(func.count()).select_from(model)) == 1
        raise RuntimeError('simulated write failure')

    with monkeypatch.context() as patch:
        patch.setattr(db, 'commit', fail_after_flush)
        with pytest.raises(RuntimeError, match='simulated write failure'):
            await client.post('/api/v1/questions/with-answer', json=payload)
    for model in (Question, Answer, QuestionImage, AnswerImage):
        assert await db.scalar(select(func.count()).select_from(model)) == 0
    await db.refresh(users[0])
    response = await client.post('/api/v1/questions/with-answer', json=payload)
    assert response.status_code == 201, response.text


@pytest.mark.parametrize('invalid', ['duplicate_stem', 'duplicate_answer', 'negative_order'])
async def test_complete_save_rejects_invalid_image_lists(db, users, client, invalid):
    images = await seed_images(db, users[0].id)
    payload = bundle(images)
    if invalid == 'duplicate_stem':
        payload['question']['stem_image_ids'] *= 2
    elif invalid == 'duplicate_answer':
        payload['answer']['images'] *= 2
    else:
        payload['answer']['images'][0]['order_index'] = -1
    response = await client.post('/api/v1/questions/with-answer', json=payload)
    assert response.status_code == 422, response.text
    assert await db.scalar(select(func.count()).select_from(Question)) == 0


async def seed_paper_set(db, user_id, count=3):
    paper = PaperSet(user_id=user_id, title='Practice')
    questions = [Question(user_id=user_id, type='OTHER') for _ in range(count)]
    db.add_all([paper, *questions])
    await db.flush()
    db.add(PaperSetItem(paper_set_id=paper.id, question_id=questions[0].id,
                        order_index=7, section_title='Original', score=3))
    await db.commit()
    items = [{'question_id': str(q.id), 'order_index': i, 'score': 0, 'section_title': 'New'}
             for i, q in enumerate(questions)]
    return paper.id, items


@pytest.mark.parametrize('count', [1, 25, 100])
async def test_batch_upsert_has_fixed_queries_and_one_commit(db, users, client, monkeypatch, count):
    paper_id, items = await seed_paper_set(db, users[0].id, count)
    selects = []
    commits = []
    original_commit = db.commit

    async def count_commit():
        commits.append(True)
        await original_commit()

    def record_query(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith('SELECT'):
            selects.append(statement)

    engine = db.bind.sync_engine
    event.listen(engine, 'before_cursor_execute', record_query)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(db, 'commit', count_commit)
            response = await client.post(f'/api/v1/paper-sets/{paper_id}/items/batch', json={'items': items})
    finally:
        event.remove(engine, 'before_cursor_execute', record_query)
    assert response.status_code == 200, response.text
    assert len(selects) == 3 and len(commits) == 1
    assert [item['question_id'] for item in response.json()] == [item['question_id'] for item in items]
    assert all(item['score'] == 0 and item['section_title'] == 'New' for item in response.json())
    assert await db.scalar(select(func.count()).select_from(PaperSetItem)) == count


@pytest.mark.parametrize('kind, status', [('foreign', 403), ('deleted', 404), ('missing', 404)])
async def test_batch_invalid_last_item_leaves_every_item_unchanged(db, users, client, kind, status):
    paper_id, items = await seed_paper_set(db, users[0].id)
    last = await db.get(Question, UUID(items[-1]['question_id']))
    if kind == 'foreign':
        last.user_id = users[1].id
    elif kind == 'deleted':
        last.is_deleted = True
    else:
        items[-1]['question_id'] = str(uuid4())
    await db.commit()
    response = await client.post(f'/api/v1/paper-sets/{paper_id}/items/batch', json={'items': items})
    assert response.status_code == status, response.text
    saved = (await db.execute(select(PaperSetItem))).scalar_one()
    assert (saved.order_index, saved.section_title, saved.score) == (7, 'Original', 3)


async def test_batch_commit_failure_rolls_back_updates_and_inserts(db, users, client, monkeypatch):
    paper_id, items = await seed_paper_set(db, users[0].id)

    async def fail_after_flush():
        await db.flush()
        assert await db.scalar(select(func.count()).select_from(PaperSetItem)) == 3
        raise RuntimeError('simulated write failure')

    with monkeypatch.context() as patch:
        patch.setattr(db, 'commit', fail_after_flush)
        with pytest.raises(RuntimeError, match='simulated write failure'):
            await client.post(f'/api/v1/paper-sets/{paper_id}/items/batch', json={'items': items})
    saved = (await db.execute(select(PaperSetItem))).scalar_one()
    assert (saved.order_index, saved.section_title, saved.score) == (7, 'Original', 3)


@pytest.mark.parametrize('invalid', ['duplicate', 'negative_order', 'negative_score', 'large_score', 'empty', 'too_many'])
async def test_batch_validates_entire_payload(db, users, client, invalid):
    paper_id, items = await seed_paper_set(db, users[0].id, 1)
    if invalid == 'duplicate':
        items *= 2
    elif invalid == 'negative_order':
        items[0]['order_index'] = -1
    elif invalid == 'negative_score':
        items[0]['score'] = -1
    elif invalid == 'large_score':
        items[0]['score'] = 10000
    elif invalid == 'empty':
        items = []
    else:
        items = [{'question_id': str(uuid4()), 'order_index': i} for i in range(1001)]
    response = await client.post(f'/api/v1/paper-sets/{paper_id}/items/batch', json={'items': items})
    assert response.status_code == 422, response.text
    saved = (await db.execute(select(PaperSetItem))).scalar_one()
    assert saved.order_index == 7 and saved.score == 3


async def test_batch_cannot_modify_another_accounts_paper_set(db, users, client):
    paper_id, items = await seed_paper_set(db, users[1].id)
    response = await client.post(f'/api/v1/paper-sets/{paper_id}/items/batch', json={'items': items})
    assert response.status_code == 403, response.text
    assert await db.scalar(select(func.count()).select_from(PaperSetItem)) == 1
