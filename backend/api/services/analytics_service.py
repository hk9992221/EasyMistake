from collections import Counter, defaultdict
from datetime import timedelta
from uuid import UUID
from sqlalchemy import select, func, case, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from api.core.datetime_utils import local_day_bounds_utc, utcnow
from api.models.attempt import Attempt, AttemptResult
from api.models.question import Question
from api.models.question_progress import QuestionProgress


class AnalyticsService:
    async def overview(self, db: AsyncSession, user_id: UUID) -> dict:
        total_questions = (
            await db.execute(
                select(func.count()).select_from(Question).where(Question.user_id == user_id, Question.is_deleted == False)
            )
        ).scalar() or 0

        mistake_questions = (
            await db.execute(
                select(func.count(func.distinct(Attempt.question_id))).join(Question).where(Question.is_deleted.is_(False),
                    Attempt.user_id == user_id, Attempt.result == AttemptResult.WRONG
                )
            )
        ).scalar() or 0

        unmastered_mistake_questions = (
            await db.execute(
                select(func.count(func.distinct(Attempt.question_id)))
                .join(Question)
                .outerjoin(QuestionProgress, and_(
                    QuestionProgress.question_id == Attempt.question_id,
                    QuestionProgress.user_id == user_id,
                ))
                .where(
                    Question.is_deleted.is_(False), Attempt.user_id == user_id,
                    Attempt.result == AttemptResult.WRONG,
                    or_(QuestionProgress.id.is_(None), QuestionProgress.is_mastered.is_(False)),
                )
            )
        ).scalar() or 0

        mastered_questions = (
            await db.execute(
                select(func.count()).select_from(QuestionProgress).join(Question).where(Question.is_deleted.is_(False),
                    QuestionProgress.user_id == user_id, QuestionProgress.is_mastered == True
                )
            )
        ).scalar() or 0

        start_of_day_utc, end_of_day_utc = local_day_bounds_utc()
        due_today = (
            await db.execute(
                select(func.count()).select_from(QuestionProgress).join(Question).where(Question.is_deleted.is_(False),
                    QuestionProgress.user_id == user_id,
                    QuestionProgress.next_review_at <= end_of_day_utc,
                )
            )
        ).scalar() or 0

        overdue = (
            await db.execute(
                select(func.count()).select_from(QuestionProgress).join(Question).where(Question.is_deleted.is_(False),
                    QuestionProgress.user_id == user_id,
                    QuestionProgress.next_review_at < start_of_day_utc,
                )
            )
        ).scalar() or 0

        acc_7d = await self._accuracy(db, user_id, days=7)
        acc_30d = await self._accuracy(db, user_id, days=30)

        return {
            "total_questions": total_questions,
            "mistake_questions": mistake_questions,
            "unmastered_mistake_questions": unmastered_mistake_questions,
            "mastered_questions": mastered_questions,
            "due_today": due_today,
            "overdue": overdue,
            "avg_accuracy_7d": round(acc_7d, 4),
            "avg_accuracy_30d": round(acc_30d, 4),
        }

    async def _accuracy(self, db: AsyncSession, user_id: UUID, days: int) -> float:
        since = utcnow() - timedelta(days=days)
        total, correct = (await db.execute(select(
            func.count(Attempt.id), func.sum(case((Attempt.result == AttemptResult.CORRECT, 1), else_=0)),
        ).join(Question).where(Attempt.user_id == user_id, Attempt.submitted_at >= since,
                              Question.is_deleted.is_(False)))).one()
        return correct / total if total else 0.0

    async def error_tags(self, db: AsyncSession, user_id: UUID, top: int = 20) -> dict:
        result = await db.execute(select(Attempt.error_tags_json).join(Question).where(Attempt.user_id == user_id, Question.is_deleted.is_(False)))
        counter: Counter[str] = Counter()
        for row in result.all():
            for tag in row[0] or []:
                counter[str(tag)] += 1
        items = [{"error_tag": tag, "count": count} for tag, count in counter.most_common(top)]
        return {"items": items}

    async def mastery_distribution(self, db: AsyncSession, user_id: UUID) -> dict:
        result = await db.execute(
            select(QuestionProgress.mastery_level, func.count())
            .join(Question).where(QuestionProgress.user_id == user_id, Question.is_deleted.is_(False))
            .group_by(QuestionProgress.mastery_level)
            .order_by(QuestionProgress.mastery_level.asc())
        )
        return {"items": [{"mastery_level": row[0], "count": row[1]} for row in result.all()]}

    async def knowledge_points(self, db: AsyncSession, user_id: UUID, top: int = 30) -> dict:
        result = await db.execute(
            select(Attempt.result, Question.knowledge_points_json)
            .join(Question, Question.id == Attempt.question_id)
            .where(Attempt.user_id == user_id, Question.is_deleted == False)
        )
        stats: dict[str, dict[str, int]] = defaultdict(lambda: {"total_attempts": 0, "wrong_attempts": 0})
        for attempt_result, points in result.all():
            for point in points or []:
                key = str(point)
                stats[key]["total_attempts"] += 1
                if attempt_result == AttemptResult.WRONG:
                    stats[key]["wrong_attempts"] += 1

        sorted_items = sorted(stats.items(), key=lambda x: x[1]["wrong_attempts"], reverse=True)[:top]
        return {
            "items": [
                {"knowledge_point": key, "total_attempts": value["total_attempts"], "wrong_attempts": value["wrong_attempts"]}
                for key, value in sorted_items
            ]
        }

    async def review_retention(self, db: AsyncSession, user_id: UUID, days: int = 30) -> dict:
        since = utcnow() - timedelta(days=days)
        result = await db.execute(
            select(Attempt.question_id, Attempt.result)
            .join(Question).where(Question.is_deleted.is_(False),Attempt.user_id == user_id, Attempt.source == "review", Attempt.submitted_at >= since)
            .order_by(Attempt.submitted_at.asc())
        )
        seen = set()
        retained = set()
        for question_id, result_value in result.all():
            seen.add(question_id)
            if result_value == AttemptResult.CORRECT:
                retained.add(question_id)

        reviewed_count = len(seen)
        retained_count = len(retained)
        retention_rate = (retained_count / reviewed_count) if reviewed_count else 0.0
        return {
            "reviewed_count": reviewed_count,
            "retained_count": retained_count,
            "retention_rate": round(retention_rate, 4),
        }


analytics_service = AnalyticsService()
