from uuid import UUID
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from api.models.attempt import Attempt, AttemptResult
from api.models.question import Question
from api.schemas.attempt import AttemptCreate, AttemptUpdate
from api.core.exceptions import NotFoundError, ForbiddenError
from api.core.datetime_utils import utcnow
from api.services.question_progress_service import question_progress_service


class AttemptService:
    """Service for attempt (practice record) operations"""

    async def create_attempt(
        self,
        db: AsyncSession,
        user_id: UUID,
        attempt_data: AttemptCreate,
    ) -> Attempt:
        # Verify question exists and user has access
        result = await db.execute(select(Question).where(Question.id == attempt_data.question_id))
        question = result.scalar_one_or_none()
        if not question:
            raise NotFoundError(detail="Question not found")

        attempt = Attempt(
            user_id=user_id,
            question_id=attempt_data.question_id,
            result=attempt_data.result,
            duration_sec=attempt_data.duration_sec,
            source=attempt_data.source,
            review_mode=attempt_data.review_mode,
            error_tags_json=attempt_data.error_tags,
            wrong_reason=attempt_data.wrong_reason,
            note=attempt_data.note,
            occurred_at=attempt_data.occurred_at or utcnow(),
            submitted_at=attempt_data.submitted_at or attempt_data.occurred_at or utcnow(),
        )

        db.add(attempt)
        await db.flush()
        await question_progress_service.apply_attempt(db, user_id, attempt)
        await db.commit()
        await db.refresh(attempt)
        return attempt

    async def list_attempts(
        self,
        db: AsyncSession,
        user_id: UUID,
        is_admin: bool = False,
        skip: int = 0,
        limit: int = 50,
        question_id: UUID = None,
        result: AttemptResult = None,
    ) -> List[Attempt]:
        query = select(Attempt).order_by(Attempt.occurred_at.desc())

        if not is_admin:
            query = query.where(Attempt.user_id == user_id)

        if question_id:
            query = query.where(Attempt.question_id == question_id)

        if result:
            query = query.where(Attempt.result == result)

        result = await db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())

    async def get_attempt(self, db: AsyncSession, attempt_id: UUID) -> Attempt:
        result = await db.execute(select(Attempt).where(Attempt.id == attempt_id))
        attempt = result.scalar_one_or_none()
        if not attempt:
            raise NotFoundError(detail="Attempt not found")
        return attempt

    async def get_user_attempts_for_question(
        self,
        db: AsyncSession,
        user_id: UUID,
        question_id: UUID,
    ) -> List[Attempt]:
        result = await db.execute(
            select(Attempt)
            .where(Attempt.user_id == user_id)
            .where(Attempt.question_id == question_id)
            .order_by(Attempt.occurred_at.desc())
        )
        return list(result.scalars().all())

    async def update_attempt(
        self,
        db: AsyncSession,
        attempt_id: UUID,
        attempt_data: AttemptUpdate,
        user_id: UUID,
        is_admin: bool = False,
    ) -> Attempt:
        attempt = await self.get_attempt(db, attempt_id)

        if not is_admin and attempt.user_id != user_id:
            raise ForbiddenError(detail="You don't have permission to update this attempt")

        update_data = attempt_data.model_dump(exclude_unset=True)
        if "error_tags" in update_data:
            update_data["error_tags_json"] = update_data.pop("error_tags") or []
        for field, value in update_data.items():
            setattr(attempt, field, value)

        await db.commit()
        await db.refresh(attempt)
        return attempt

    async def delete_attempt(
        self,
        db: AsyncSession,
        attempt_id: UUID,
        user_id: UUID,
        is_admin: bool = False,
    ) -> None:
        attempt = await self.get_attempt(db, attempt_id)

        if not is_admin and attempt.user_id != user_id:
            raise ForbiddenError(detail="You don't have permission to delete this attempt")

        await db.delete(attempt)
        await db.commit()

    async def get_mistakes_analysis(
        self,
        db: AsyncSession,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> List[dict]:
        """Get user's wrong attempts for mistakes analysis"""
        result = await db.execute(
            select(Attempt, Question)
            .join(Question, Attempt.question_id == Question.id)
            .where(Attempt.user_id == user_id)
            .where(Attempt.result == AttemptResult.WRONG)
            .where(Question.is_deleted == False)
            .order_by(Attempt.occurred_at.desc())
            .offset(skip)
            .limit(limit)
        )

        mistakes = []
        for attempt, question in result.all():
            mistakes.append({
                "attempt": attempt,
                "question": question,
            })

        return mistakes

    async def get_attempt_stats(
        self,
        db: AsyncSession,
        user_id: UUID,
    ) -> dict:
        total_attempts_result = await db.execute(
            select(func.count()).where(Attempt.user_id == user_id)
        )
        total_attempts = total_attempts_result.scalar() or 0

        wrong_questions_result = await db.execute(
            select(func.count(func.distinct(Attempt.question_id))).where(
                Attempt.user_id == user_id,
                Attempt.result == AttemptResult.WRONG,
            )
        )
        total_wrong_questions = wrong_questions_result.scalar() or 0

        latest_per_question = (
            select(
                Attempt.question_id.label("question_id"),
                func.max(Attempt.occurred_at).label("latest_occurred_at"),
            )
            .where(Attempt.user_id == user_id)
            .group_by(Attempt.question_id)
            .subquery()
        )

        unmastered_result = await db.execute(
            select(func.count())
            .select_from(Attempt)
            .join(
                latest_per_question,
                (Attempt.question_id == latest_per_question.c.question_id)
                & (Attempt.occurred_at == latest_per_question.c.latest_occurred_at),
            )
            .where(
                Attempt.user_id == user_id,
                Attempt.result == AttemptResult.WRONG,
            )
        )
        unmastered_wrong_questions = unmastered_result.scalar() or 0

        return {
            "total_attempts": total_attempts,
            "total_wrong_questions": total_wrong_questions,
            "unmastered_wrong_questions": unmastered_wrong_questions,
        }


attempt_service = AttemptService()
