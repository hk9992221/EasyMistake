from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.core.deps import get_db, get_current_user
from api.models.user import User, UserRole
from api.models.answer import Answer
from api.models.question_image import QuestionImage
from api.schemas.answer import AnswerResponse
from api.schemas.question import QuestionResponse, QuestionImageItem
from api.schemas.review import (
    ReviewQueueResponse, ReviewQueueItem, DailyReviewPaperSetRequest, DailyReviewPaperSetResponse,
)
from api.schemas.question_progress import ReviewCompleteRequest
from api.services.review_service import review_service
from api.core.datetime_utils import local_date
from api.core.image_urls import build_image_proxy_url


router = APIRouter(prefix="/reviews", tags=["reviews"])


async def _queue_response(
    db: AsyncSession, current_user: User, request: Request, today_only: bool,
    page: int, page_size: int, subject: str | None, include_details: bool,
) -> ReviewQueueResponse:
    day = local_date()
    rows, total, subjects = await review_service.get_queue_page(
        db, current_user.id, today_only, page, page_size, subject,
        is_admin=current_user.role == UserRole.ADMIN, review_date=day,
    )
    items = [ReviewQueueItem(**review_service.queue_item(progress)) for progress, _ in rows]
    if include_details and rows:
        ids = [question.id for _, question in rows]
        answers = {answer.question_id: answer for answer in (await db.execute(
            select(Answer).where(Answer.question_id.in_(ids)).options(selectinload(Answer.images))
        )).scalars().all()}
        stem_images = {}
        for link in (await db.execute(select(QuestionImage).where(QuestionImage.question_id.in_(ids))
                     .order_by(QuestionImage.order_index, QuestionImage.image_id))).scalars().all():
            stem_images.setdefault(link.question_id, []).append(QuestionImageItem(
                image_id=link.image_id, order_index=link.order_index,
                url=build_image_proxy_url(request, link.image_id),
            ))
        for item, (_, question) in zip(items, rows):
            item.question = QuestionResponse.model_validate(question)
            item.question.proficiency_score = item.proficiency_score
            item.question.stem_images = stem_images.get(question.id, [])
            if question.id in answers:
                item.answer = AnswerResponse.model_validate(answers[question.id])
                item.answer.images.sort(key=lambda image: (image.order_index, str(image.image_id)))
                for image in item.answer.images:
                    image.url = build_image_proxy_url(request, image.image_id)
    return ReviewQueueResponse(
        date=day, items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size, subjects=subjects,
    )


@router.get("/today", response_model=ReviewQueueResponse)
async def get_today_reviews(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=100),
    subject: str | None = Query(None, min_length=1, max_length=64),
    include_details: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _queue_response(db, current_user, request, True, page, page_size, subject, include_details)


@router.get("/queue", response_model=ReviewQueueResponse)
async def get_review_queue(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=100),
    subject: str | None = Query(None, min_length=1, max_length=64),
    include_details: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _queue_response(db, current_user, request, False, page, page_size, subject, include_details)


@router.post("/daily-paper-set", response_model=DailyReviewPaperSetResponse)
async def generate_daily_paper_set(
    payload: DailyReviewPaperSetRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await review_service.generate_daily_paper_set(
        db, current_user.id, payload.subject, is_admin=current_user.role == UserRole.ADMIN,
    )


@router.post("/{question_id}/complete")
async def complete_review(
    question_id: UUID,
    payload: ReviewCompleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attempt = await review_service.complete_review(db, current_user.id, question_id, payload, is_admin=current_user.role == "ADMIN")
    return {"attempt_id": str(attempt.id)}


@router.post("/recalculate")
async def recalculate_review_queue(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = await review_service.recalculate(db, current_user.id)
    return {"updated": count}
