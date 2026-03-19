from datetime import timedelta
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from api.core.datetime_utils import utcnow
from api.core.exceptions import NotFoundError, ForbiddenError
from api.models.attempt import Attempt, AttemptResult
from api.models.question_progress import QuestionProgress
from api.schemas.question_progress import QuestionProgressUpdate


REVIEW_INTERVAL_DAYS = [1, 2, 4, 7, 15, 30]


class QuestionProgressService:
    async def create_progress(self, db: AsyncSession, user_id: UUID, question_id: UUID) -> QuestionProgress:
        progress = await self.get_or_create_progress(db, user_id, question_id)
        await db.commit()
        await db.refresh(progress)
        return progress

    async def get_or_create_progress(self, db: AsyncSession, user_id: UUID, question_id: UUID) -> QuestionProgress:
        result = await db.execute(
            select(QuestionProgress).where(
                QuestionProgress.user_id == user_id,
                QuestionProgress.question_id == question_id,
            )
        )
        progress = result.scalar_one_or_none()
        if progress:
            return progress

        progress = QuestionProgress(user_id=user_id, question_id=question_id, next_review_at=utcnow())
        db.add(progress)
        await db.flush()
        return progress

    def _calc_mastery_level(self, score: int) -> int:
        if score < 40:
            return 0
        if score < 60:
            return 1
        if score < 80:
            return 2
        return 3

    def _next_interval_days(self, review_stage: int) -> int:
        idx = max(0, min(review_stage, len(REVIEW_INTERVAL_DAYS) - 1))
        return REVIEW_INTERVAL_DAYS[idx]

    def _calculate_new_score(self, progress: QuestionProgress, attempt: Attempt) -> int:
        score = progress.proficiency_score or 50
        if attempt.result == AttemptResult.CORRECT:
            score += 10
            if progress.consecutive_correct >= 2:
                score += 5
        elif attempt.result == AttemptResult.WRONG:
            score -= 15
            tags = set(attempt.error_tags_json or [])
            if "KNOWLEDGE" in tags or "METHOD" in tags:
                score -= 10
        elif attempt.result == AttemptResult.PARTIAL:
            score += 2
        else:
            score -= 2

        if attempt.duration_sec and attempt.duration_sec > 180:
            score -= 5

        return max(0, min(100, score))

    def _update_counts(self, progress: QuestionProgress, attempt: Attempt) -> None:
        progress.total_attempts += 1
        if attempt.result == AttemptResult.CORRECT:
            progress.correct_attempts += 1
            progress.consecutive_correct += 1
            progress.review_stage = min(progress.review_stage + 1, len(REVIEW_INTERVAL_DAYS) - 1)
        elif attempt.result == AttemptResult.WRONG:
            progress.wrong_attempts += 1
            progress.consecutive_correct = 0
            if progress.review_stage <= 2:
                progress.review_stage = 0
            else:
                progress.review_stage = max(0, progress.review_stage - 2)
        else:
            progress.consecutive_correct = 0
            progress.review_stage = max(0, progress.review_stage - 1)

    async def apply_attempt(self, db: AsyncSession, user_id: UUID, attempt: Attempt) -> QuestionProgress:
        progress = await self.get_or_create_progress(db, user_id, attempt.question_id)
        self._update_counts(progress, attempt)

        progress.last_result = attempt.result
        progress.last_reviewed_at = attempt.submitted_at or attempt.occurred_at
        progress.proficiency_score = self._calculate_new_score(progress, attempt)
        progress.mastery_level = self._calc_mastery_level(progress.proficiency_score)
        progress.is_mastered = progress.mastery_level >= 3 and progress.consecutive_correct >= 3

        interval_days = self._next_interval_days(progress.review_stage)
        progress.next_review_at = utcnow() + timedelta(days=interval_days)
        await db.flush()
        return progress

    async def list_progress(
        self,
        db: AsyncSession,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
        question_id: UUID | None = None,
        due_only: bool = False,
    ) -> tuple[list[QuestionProgress], int]:
        query = select(QuestionProgress).where(QuestionProgress.user_id == user_id)
        count_query = select(func.count()).select_from(QuestionProgress).where(QuestionProgress.user_id == user_id)
        if question_id:
            query = query.where(QuestionProgress.question_id == question_id)
            count_query = count_query.where(QuestionProgress.question_id == question_id)
        if due_only:
            now = utcnow()
            query = query.where(QuestionProgress.next_review_at <= now)
            count_query = count_query.where(QuestionProgress.next_review_at <= now)

        query = query.order_by(QuestionProgress.next_review_at.asc().nullsfirst(), QuestionProgress.updated_at.desc())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        rows = await db.execute(query.offset(offset).limit(page_size))
        return list(rows.scalars().all()), total

    async def get_progress(self, db: AsyncSession, progress_id: UUID, user_id: UUID, is_admin: bool = False) -> QuestionProgress:
        result = await db.execute(select(QuestionProgress).where(QuestionProgress.id == progress_id))
        progress = result.scalar_one_or_none()
        if not progress:
            raise NotFoundError(detail="Question progress not found")
        if not is_admin and progress.user_id != user_id:
            raise ForbiddenError(detail="You don't have permission to access this progress")
        return progress

    async def update_progress(
        self,
        db: AsyncSession,
        progress_id: UUID,
        payload: QuestionProgressUpdate,
        user_id: UUID,
        is_admin: bool = False,
    ) -> QuestionProgress:
        progress = await self.get_progress(db, progress_id, user_id, is_admin=is_admin)
        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(progress, field, value)
        await db.commit()
        await db.refresh(progress)
        return progress


question_progress_service = QuestionProgressService()
