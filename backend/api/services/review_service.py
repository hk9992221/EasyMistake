from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.core.datetime_utils import local_day_bounds_utc, utcnow
from api.models.question_progress import QuestionProgress
from api.models.question import Question
from api.services.question_progress_service import question_progress_service
from api.schemas.question_progress import ReviewCompleteRequest
from api.schemas.attempt import AttemptCreate
from api.models.attempt import AttemptResult
from api.services.attempt_service import attempt_service


class ReviewService:
    def _priority(self, progress: QuestionProgress) -> tuple[int, str]:
        now = utcnow()
        overdue_hours = 0
        if progress.next_review_at and progress.next_review_at < now:
            overdue_hours = int((now - progress.next_review_at).total_seconds() // 3600)
        priority = min(100, 50 + overdue_hours + (100 - (progress.proficiency_score if progress.proficiency_score is not None else 50)) // 2)
        if overdue_hours > 0 and (progress.mastery_level or 0) <= 1:
            reason = "overdue_and_low_mastery"
        elif progress.last_result == AttemptResult.WRONG.value:
            reason = "recent_wrong_answer"
        else:
            reason = "scheduled_review"
        return priority, reason

    async def get_queue(self, db: AsyncSession, user_id: UUID, today_only: bool = False, limit: int = 100) -> list[dict]:
        now = utcnow()
        query = select(QuestionProgress).join(Question).where(QuestionProgress.user_id == user_id, Question.is_deleted.is_(False))
        if today_only:
            _, end_of_day_utc = local_day_bounds_utc()
            query = query.where(QuestionProgress.next_review_at <= end_of_day_utc)
        query = query.order_by(QuestionProgress.next_review_at.asc().nullsfirst(), QuestionProgress.proficiency_score.asc())
        result = await db.execute(query.limit(limit))
        items = []
        for progress in result.scalars().all():
            priority, reason = self._priority(progress)
            items.append(
                {
                    "question_id": progress.question_id,
                    "progress_id": progress.id,
                    "priority": priority,
                    "reason": reason,
                    "review_stage": progress.review_stage,
                    "next_review_at": progress.next_review_at,
                    "proficiency_score": progress.proficiency_score,
                }
            )
        return items

    async def complete_review(
        self,
        db: AsyncSession,
        user_id: UUID,
        question_id: UUID,
        payload: ReviewCompleteRequest,
        is_admin: bool = False,
    ):
        attempt_data = AttemptCreate(
            question_id=question_id,
            result=AttemptResult(payload.result),
            duration_sec=payload.duration_sec,
            source="review",
            review_mode="scheduled_review",
            error_tags=payload.error_tags,
            note=payload.note,
        )
        return await attempt_service.create_attempt(db, user_id, attempt_data, is_admin=is_admin)

    async def recalculate(self, db: AsyncSession, user_id: UUID) -> int:
        ids = (await db.execute(select(QuestionProgress.question_id).join(Question).where(
            QuestionProgress.user_id == user_id, Question.is_deleted.is_(False),
        ).order_by(QuestionProgress.question_id))).scalars().all()
        for question_id in ids:
            await db.execute(select(Question.id).where(Question.id == question_id).with_for_update())
            await question_progress_service.rebuild_progress(db, user_id, question_id)
        await db.commit()
        return len(ids)


review_service = ReviewService()
