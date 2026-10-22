from uuid import UUID
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from api.models.paper_set import PaperSet
from api.models.paper_set_item import PaperSetItem
from api.models.question import Question
from api.models.attempt import Attempt
from api.models.question_progress import QuestionProgress
from api.schemas.attempt import AttemptResponse
from api.schemas.question_progress import QuestionProgressResponse
from api.schemas.paper_set import (
    PaperSetCreate,
    PaperSetUpdate,
    PaperSetItemCreate,
    PaperSetItemUpdate,
    PaperSetPreviewResponse,
    PaperSetReviewDataResponse,
    PreviewQuestion,
    BatchUpsertPaperSetRequest,
)
from api.core.exceptions import NotFoundError, ForbiddenError
from api.core.access import require_question_access


class PaperSetService:
    """Service for paper set operations"""

    async def create_paper_set(
        self,
        db: AsyncSession,
        user_id: UUID,
        paper_set_data: PaperSetCreate,
    ) -> PaperSet:
        paper_set = PaperSet(
            user_id=user_id,
            title=paper_set_data.title,
            subject=paper_set_data.subject,
            description=paper_set_data.description,
            output_format=paper_set_data.output_format,
            render_options=paper_set_data.render_options,
        )

        db.add(paper_set)
        await db.commit()
        await db.refresh(paper_set)
        return paper_set

    async def list_paper_sets(
        self,
        db: AsyncSession,
        user_id: UUID,
        is_admin: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> List[PaperSet]:
        query = select(PaperSet).order_by(PaperSet.created_at.desc())
        if not is_admin:
            query = query.where(PaperSet.user_id == user_id)

        result = await db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())

    async def get_paper_set(self, db: AsyncSession, paper_set_id: UUID) -> PaperSet:
        result = await db.execute(select(PaperSet).where(PaperSet.id == paper_set_id))
        return result.scalar_one_or_none()

    async def update_paper_set(
        self,
        db: AsyncSession,
        paper_set_id: UUID,
        paper_set_data: PaperSetUpdate,
        user_id: UUID,
        is_admin: bool = False,
    ) -> PaperSet:
        paper_set = await self.get_paper_set(db, paper_set_id)
        if not paper_set:
            raise NotFoundError(detail="Paper set not found")

        if not is_admin and paper_set.user_id != user_id:
            raise ForbiddenError(detail="You don't have permission to update this paper set")

        update_data = paper_set_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(paper_set, field, value)

        await db.commit()
        await db.refresh(paper_set)
        return paper_set

    async def delete_paper_set(
        self,
        db: AsyncSession,
        paper_set_id: UUID,
        user_id: UUID,
        is_admin: bool = False,
    ) -> None:
        paper_set = await self.get_paper_set(db, paper_set_id)
        if not paper_set:
            raise NotFoundError(detail="Paper set not found")

        if not is_admin and paper_set.user_id != user_id:
            raise ForbiddenError(detail="You don't have permission to delete this paper set")

        await db.delete(paper_set)
        await db.commit()

    async def upsert_item(
        self,
        db: AsyncSession,
        paper_set_id: UUID,
        question_id: UUID,
        item_data: PaperSetItemCreate,
        user_id: UUID,
        is_admin: bool = False,
    ) -> PaperSetItem:
        await self._ensure_paper_set_access(db, paper_set_id, user_id, is_admin, lock=True)
        await self._ensure_question_access(db, question_id, user_id, is_admin)

        result = await db.execute(
            select(PaperSetItem).where(
                PaperSetItem.paper_set_id == paper_set_id,
                PaperSetItem.question_id == question_id,
            )
        )
        item = result.scalar_one_or_none()

        if item:
            item.order_index = item_data.order_index
            item.section_title = item_data.section_title
            item.score = item_data.score if item_data.score is not None else None
        else:
            item = PaperSetItem(
                paper_set_id=paper_set_id,
                question_id=question_id,
                order_index=item_data.order_index,
                section_title=item_data.section_title,
                score=item_data.score if item_data.score is not None else None,
            )
            db.add(item)

        await db.commit()
        await db.refresh(item)
        return item

    async def update_item(
        self,
        db: AsyncSession,
        paper_set_id: UUID,
        question_id: UUID,
        item_data: PaperSetItemUpdate,
        user_id: UUID,
        is_admin: bool = False,
    ) -> PaperSetItem:
        await self._ensure_paper_set_access(db, paper_set_id, user_id, is_admin, lock=True)

        result = await db.execute(
            select(PaperSetItem).where(
                PaperSetItem.paper_set_id == paper_set_id,
                PaperSetItem.question_id == question_id,
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError(detail="Paper set item not found")

        update_data = item_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            # Handle score field specifically to avoid type issues
            if field == "score" and value is not None:
                setattr(item, field, value)
            elif value is not None:
                setattr(item, field, value)

        await db.commit()
        await db.refresh(item)
        return item

    async def delete_item(
        self,
        db: AsyncSession,
        paper_set_id: UUID,
        question_id: UUID,
        user_id: UUID,
        is_admin: bool = False,
    ) -> None:
        await self._ensure_paper_set_access(db, paper_set_id, user_id, is_admin, lock=True)

        result = await db.execute(
            select(PaperSetItem).where(
                PaperSetItem.paper_set_id == paper_set_id,
                PaperSetItem.question_id == question_id,
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError(detail="Paper set item not found")

        await db.delete(item)
        await db.commit()

    async def batch_upsert_items(
        self,
        db: AsyncSession,
        paper_set_id: UUID,
        request: BatchUpsertPaperSetRequest,
        user_id: UUID,
        is_admin: bool = False,
    ) -> List[PaperSetItem]:
        await self._ensure_paper_set_access(db, paper_set_id, user_id, is_admin, lock=True)
        question_ids = [item.question_id for item in request.items]
        questions = (await db.execute(select(Question).where(Question.id.in_(question_ids))
                     .order_by(Question.id).with_for_update()
                     .execution_options(populate_existing=True))).scalars().all()
        if len(questions) != len(question_ids) or any(question.is_deleted for question in questions):
            raise NotFoundError(detail="One or more questions are missing or deleted")
        if not is_admin and any(question.user_id != user_id for question in questions):
            raise ForbiddenError(detail="You don't have permission to access one or more questions")

        existing = {item.question_id: item for item in (await db.execute(select(PaperSetItem).where(
            PaperSetItem.paper_set_id == paper_set_id, PaperSetItem.question_id.in_(question_ids),
        ))).scalars().all()}
        results = []
        for data in request.items:
            item = existing.get(data.question_id)
            if item is None:
                item = PaperSetItem(paper_set_id=paper_set_id, question_id=data.question_id)
                db.add(item)
            item.order_index = data.order_index
            item.section_title = data.section_title
            item.score = data.score
            results.append(item)
        await db.commit()
        return results

    async def preview_paper_set(
        self,
        db: AsyncSession,
        paper_set_id: UUID,
        user_id: UUID,
        is_admin: bool = False,
    ) -> PaperSetPreviewResponse:
        paper_set = await self.get_paper_set(db, paper_set_id)
        if not paper_set:
            raise NotFoundError(detail="Paper set not found")

        if not is_admin and paper_set.user_id != user_id:
            raise ForbiddenError(detail="You don't have permission to access this paper set")

        result = await db.execute(
            select(PaperSetItem, Question)
            .join(Question, PaperSetItem.question_id == Question.id)
            .where(PaperSetItem.paper_set_id == paper_set_id)
            .order_by(PaperSetItem.order_index)
        )

        items = []
        for item, question in result.all():
            items.append(
                PreviewQuestion(
                    id=question.id,
                    order_index=item.order_index,
                    section_title=item.section_title,
                    score=float(item.score) if item.score else None,
                    subject=question.subject,
                    book_name=question.book_name,
                    chapter_name=question.chapter_name,
                    page_no=question.page_no,
                    question_no=question.question_no,
                    source_anchor=question.source_anchor,
                    type=question.type,
                    stem_text=question.stem_text,
                    stem_latex=question.stem_latex,
                    appendix=question.appendix,
                    content_json=question.content_json,
                )
            )

        return PaperSetPreviewResponse(
            paper_set_id=paper_set.id,
            title=paper_set.title,
            subject=paper_set.subject,
            description=paper_set.description,
            output_format=paper_set.output_format,
            questions=items,
        )

    async def review_data(
        self,
        db: AsyncSession,
        paper_set_id: UUID,
        user_id: UUID,
        is_admin: bool = False,
    ) -> PaperSetReviewDataResponse:
        await self._ensure_paper_set_access(db, paper_set_id, user_id, is_admin)
        question_ids = (await db.execute(
            select(PaperSetItem.question_id).where(PaperSetItem.paper_set_id == paper_set_id)
        )).scalars().all()
        if not question_ids:
            return PaperSetReviewDataResponse(attempts={}, progress={})

        attempts = (await db.execute(
            select(Attempt).where(Attempt.user_id == user_id, Attempt.question_id.in_(question_ids))
            .order_by(Attempt.occurred_at.desc(), Attempt.id.desc())
        )).scalars().all()
        progress = (await db.execute(
            select(QuestionProgress).where(
                QuestionProgress.user_id == user_id,
                QuestionProgress.question_id.in_(question_ids),
            )
        )).scalars().all()

        by_question: dict[str, list[AttemptResponse]] = {}
        for attempt in attempts:
            by_question.setdefault(str(attempt.question_id), []).append(AttemptResponse.model_validate(attempt))
        return PaperSetReviewDataResponse(
            attempts=by_question,
            progress={str(item.question_id): QuestionProgressResponse.model_validate(item) for item in progress},
        )

    async def _ensure_paper_set_access(
        self,
        db: AsyncSession,
        paper_set_id: UUID,
        user_id: UUID,
        is_admin: bool,
        lock: bool = False,
    ) -> None:
        query = select(PaperSet).where(PaperSet.id == paper_set_id)
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        paper_set = (await db.execute(query)).scalar_one_or_none()
        if not paper_set:
            raise NotFoundError(detail="Paper set not found")

        if not is_admin and paper_set.user_id != user_id:
            raise ForbiddenError(detail="You don't have permission to access this paper set")

    async def _ensure_question_access(
        self,
        db: AsyncSession,
        question_id: UUID,
        user_id: UUID,
        is_admin: bool,
    ) -> None:
        await require_question_access(db, question_id, user_id, is_admin)


paper_set_service = PaperSetService()
