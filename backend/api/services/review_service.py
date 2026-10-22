from uuid import UUID
from datetime import date, datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from api.core.datetime_utils import local_date, local_day_bounds_utc, utcnow
from api.core.exceptions import BadRequestError
from api.models.question_progress import QuestionProgress
from api.models.question import Question
from api.services.question_progress_service import question_progress_service
from api.schemas.question_progress import ReviewCompleteRequest
from api.schemas.attempt import AttemptCreate
from api.models.attempt import AttemptResult
from api.services.attempt_service import attempt_service
from api.models.user import User
from api.models.paper_set import PaperSet
from api.models.paper_set_item import PaperSetItem
from api.schemas.review import DailyReviewPaperSetResponse


class ReviewService:
    def _priority(self, progress: QuestionProgress, now: datetime | None = None) -> tuple[int, str]:
        now = now or utcnow()
        overdue_hours = 0
        due = progress.next_review_at
        if due is not None:
            due = due.replace(tzinfo=timezone.utc) if due.tzinfo is None else due
            if due < now:
                overdue_hours = int((now - due).total_seconds() // 3600)
        priority = min(100, 50 + overdue_hours + (100 - (progress.proficiency_score if progress.proficiency_score is not None else 50)) // 2)
        if overdue_hours > 0 and (progress.mastery_level or 0) <= 1:
            reason = "overdue_and_low_mastery"
        elif progress.last_result == AttemptResult.WRONG.value:
            reason = "recent_wrong_answer"
        else:
            reason = "scheduled_review"
        return priority, reason

    def _queue_query(self, user_id: UUID, today_only: bool, subject: str | None = None,
                     is_admin: bool = False, review_date: date | None = None):
        query = select(QuestionProgress, Question).select_from(QuestionProgress).join(Question).where(
            QuestionProgress.user_id == user_id, Question.is_deleted.is_(False),
        )
        if not is_admin:
            query = query.where(Question.user_id == user_id)
        if today_only:
            _, end_of_day_utc = local_day_bounds_utc(review_date)
            query = query.where(QuestionProgress.next_review_at <= end_of_day_utc)
        if subject is not None:
            query = query.where(Question.subject == subject)
        return query

    def _ordered(self, query):
        return query.order_by(
            QuestionProgress.next_review_at.asc().nullslast(),
            QuestionProgress.proficiency_score.asc(), QuestionProgress.id.asc(),
        )

    def queue_item(self, progress: QuestionProgress) -> dict:
        priority, reason = self._priority(progress)
        return {
            "question_id": progress.question_id,
            "progress_id": progress.id,
            "priority": priority,
            "reason": reason,
            "review_stage": progress.review_stage,
            "next_review_at": progress.next_review_at,
            "proficiency_score": progress.proficiency_score,
        }

    async def get_queue(self, db: AsyncSession, user_id: UUID, today_only: bool = False,
                        limit: int = 100) -> list[dict]:
        query = self._ordered(self._queue_query(user_id, today_only)).limit(limit)
        return [self.queue_item(progress) for progress, _ in (await db.execute(query)).all()]

    async def get_queue_page(self, db: AsyncSession, user_id: UUID, today_only: bool,
                             page: int, page_size: int, subject: str | None = None,
                             is_admin: bool = False, review_date: date | None = None):
        query = self._queue_query(user_id, today_only, subject, is_admin, review_date)
        total = await db.scalar(select(func.count()).select_from(query.subquery()))
        # Subject choices use the same queue, before the selected subject filter.
        subjects_query = self._queue_query(user_id, today_only, is_admin=is_admin, review_date=review_date)
        subjects = (await db.execute(subjects_query.with_only_columns(Question.subject)
                    .where(Question.subject.is_not(None), Question.subject != "")
                    .distinct().order_by(Question.subject))).scalars().all()
        rows = (await db.execute(self._ordered(query).offset((page - 1) * page_size).limit(page_size))).all()
        return rows, total, list(subjects)

    async def generate_daily_paper_set(self, db: AsyncSession, user_id: UUID,
                                       subject: str | None = None, is_admin: bool = False) -> DailyReviewPaperSetResponse:
        # Serialize generation for one user, including requests from multiple tabs.
        await db.execute(select(User.id).where(User.id == user_id).with_for_update())
        day = local_date()
        query = self._ordered(self._queue_query(user_id, True, subject, is_admin, day))
        question_ids = list((await db.execute(query.with_only_columns(QuestionProgress.question_id))).scalars())
        if not question_ids:
            raise BadRequestError(detail="当前筛选下没有待复习题目")

        key = f"{day.isoformat()}:{subject or ''}"
        paper_set = (await db.execute(select(PaperSet).where(
            PaperSet.user_id == user_id,
            PaperSet.render_options["daily_review_key"].as_string() == key,
        ).order_by(PaperSet.created_at, PaperSet.id).with_for_update())).scalars().first()
        reused = paper_set is not None
        if paper_set is None:
            paper_set = PaperSet(
                user_id=user_id,
                title=f"复习-{day.isoformat()}" + (f"-{subject}" if subject else ""),
                subject=subject or "复习", description=f"每日复习自动组卷（{day.isoformat()}）",
                output_format="LATEX", render_options={"daily_review_key": key},
            )
            db.add(paper_set)
            await db.flush()

        existing = {item.question_id: item for item in (await db.execute(
            select(PaperSetItem).where(PaperSetItem.paper_set_id == paper_set.id)
        )).scalars().all()}
        wanted = set(question_ids)
        for question_id, item in existing.items():
            if question_id not in wanted:
                await db.delete(item)
        for index, question_id in enumerate(question_ids, start=1):
            if question_id in existing:
                existing[question_id].order_index = index
            else:
                db.add(PaperSetItem(paper_set_id=paper_set.id, question_id=question_id, order_index=index))
        # The whole set is committed once; a failure rolls back all item changes.
        response = DailyReviewPaperSetResponse(
            paper_set_id=paper_set.id, title=paper_set.title, item_count=len(question_ids), reused=reused,
        )
        await db.commit()
        return response

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
