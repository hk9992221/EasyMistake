from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.deps import get_db, get_current_user
from api.models.user import User
from api.schemas.review import ReviewQueueResponse, ReviewQueueItem
from api.schemas.question_progress import ReviewCompleteRequest
from api.services.review_service import review_service
from api.core.datetime_utils import local_date


router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("/today", response_model=ReviewQueueResponse)
async def get_today_reviews(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = await review_service.get_queue(db, current_user.id, today_only=True)
    return ReviewQueueResponse(date=local_date(), items=[ReviewQueueItem.model_validate(x) for x in items])


@router.get("/queue", response_model=ReviewQueueResponse)
async def get_review_queue(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = await review_service.get_queue(db, current_user.id, today_only=False)
    return ReviewQueueResponse(date=local_date(), items=[ReviewQueueItem.model_validate(x) for x in items])


@router.post("/{question_id}/complete")
async def complete_review(
    question_id: UUID,
    payload: ReviewCompleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attempt = await review_service.complete_review(db, current_user.id, question_id, payload)
    return {"attempt_id": str(attempt.id)}


@router.post("/recalculate")
async def recalculate_review_queue(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = await review_service.recalculate(db, current_user.id)
    return {"updated": count}
