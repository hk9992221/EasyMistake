from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from api.models import Answer, Question, QuestionProgress, UserRole


async def test_restore_keeps_answer_and_learning_progress(db, users, client):
    created = await client.post('/api/v1/questions/with-answer', json={
        'request_id': str(uuid4()), 'question': {'type': 'OTHER', 'stem_text': 'Recover me'},
        'answer': {'answer_type': 'TEXT', 'answer_text': 'Preserved answer'},
    })
    qid = UUID(created.json()['id'])
    db.add(QuestionProgress(user_id=users[0].id, question_id=qid, total_attempts=5, proficiency_score=72))
    await db.commit()
    assert (await client.delete(f'/api/v1/questions/{qid}')).status_code == 200
    assert (await client.get(f'/api/v1/questions/{qid}')).status_code == 404
    await db.refresh(users[0])
    trash = await client.get('/api/v1/questions/trash')
    assert trash.json()['items'][0]['id'] == str(qid) and trash.json()['total'] == 1
    for _ in range(2):
        response = await client.post(f'/api/v1/questions/{qid}/restore')
        assert response.status_code == 200 and not response.json()['is_deleted']
    assert (await client.get('/api/v1/questions/trash')).json()['total'] == 0
    assert (await client.get(f'/api/v1/questions/{qid}/answer')).json()['answer_text'] == 'Preserved answer'
    progress = (await db.execute(select(QuestionProgress))).scalar_one()
    assert (progress.total_attempts, progress.proficiency_score) == (5, 72)
    assert await db.scalar(select(func.count()).select_from(Answer)) == 1


@pytest.mark.parametrize('admin', [False, True])
async def test_trash_and_restore_enforce_ownership(db, users, client, admin):
    users[0].role = UserRole.ADMIN if admin else UserRole.USER
    questions = [Question(user_id=user.id, type='OTHER', is_deleted=True) for user in users]
    db.add_all(questions)
    await db.commit()
    other_id = questions[1].id
    response = await client.get('/api/v1/questions/trash?page_size=1')
    assert response.status_code == 200 and response.json()['total'] == (2 if admin else 1)
    assert len(response.json()['items']) == 1
    if not admin:
        assert response.json()['items'][0]['user_id'] == str(users[0].id)
    response = await client.post(f'/api/v1/questions/{other_id}/restore')
    assert response.status_code == (200 if admin else 403), response.text
    question = await db.get(Question, other_id)
    assert question.is_deleted != admin


async def test_missing_question_cannot_be_restored(db, users, client):
    response = await client.post(f'/api/v1/questions/{uuid4()}/restore')
    assert response.status_code == 404
    assert await db.scalar(select(func.count()).select_from(Question)) == 0
