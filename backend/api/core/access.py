from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.models.question import Question
from api.core.exceptions import NotFoundError, ForbiddenError


async def require_question_access(db: AsyncSession, question_id: UUID, user_id: UUID, is_admin: bool = False):
    question = (await db.execute(select(Question).where(Question.id == question_id).with_for_update())).scalar_one_or_none()
    if question is None or question.is_deleted:
        raise NotFoundError(detail="Question not found")
    if not is_admin and question.user_id != user_id:
        raise ForbiddenError(detail="You don't have access to this question")
    return question


async def require_owned_resources(db, model, resource_ids, user_id, is_admin=False):
    ids = set(resource_ids)
    if not ids:
        return
    rows = (await db.execute(select(model).where(model.id.in_(ids)))).scalars().all()
    if len(rows) != len(ids):
        raise NotFoundError(detail="One or more resources not found")
    if not is_admin and any(row.user_id != user_id for row in rows):
        raise ForbiddenError(detail="You don't have access to one or more resources")
