from uuid import UUID
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from api.models.paper_set import PaperSet
from api.models.paper_set_item import PaperSetItem
from api.models.question import Question
from api.schemas.paper_set import (
    PaperSetCreate,
    PaperSetUpdate,
    PaperSetItemCreate,
    PaperSetItemUpdate,
    PaperSetItemResponse,
    PaperSetPreviewResponse,
    PreviewQuestion,
    BatchUpsertPaperSetRequest,
)
from api.core.exceptions import NotFoundError, ForbiddenError


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
        await self._ensure_paper_set_access(db, paper_set_id, user_id, is_admin)
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
            # Convert float to None if 0.0, otherwise keep the value
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
        await self._ensure_paper_set_access(db, paper_set_id, user_id, is_admin)

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
        await self._ensure_paper_set_access(db, paper_set_id, user_id, is_admin)

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
    ) -> List[PaperSetItemResponse]:
        await self._ensure_paper_set_access(db, paper_set_id, user_id, is_admin)

        results = []
        for item in request.items:
            await self._ensure_question_access(db, item.question_id, user_id, is_admin)
            result = await self.upsert_item(
                db,
                paper_set_id,
                item.question_id,
                PaperSetItemCreate(
                    question_id=item.question_id,
                    order_index=item.order_index,
                    section_title=item.section_title,
                    score=item.score,
                ),
                user_id,
                is_admin=is_admin,
            )
            results.append(result)

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

    async def _ensure_paper_set_access(
        self,
        db: AsyncSession,
        paper_set_id: UUID,
        user_id: UUID,
        is_admin: bool,
    ) -> None:
        paper_set = await self.get_paper_set(db, paper_set_id)
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
        result = await db.execute(select(Question).where(Question.id == question_id))
        question = result.scalar_one_or_none()
        if not question:
            raise NotFoundError(detail="Question not found")

        if not is_admin and question.user_id != user_id:
            raise ForbiddenError(detail="You don't have permission to access this question")


paper_set_service = PaperSetService()
