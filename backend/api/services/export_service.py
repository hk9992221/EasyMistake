from uuid import UUID
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from api.models.export import Export, ExportStatus
from api.models.export_item import ExportItem
from api.models.question import Question
from api.models.question_image import QuestionImage
from api.models.image import Image
from api.models.paper_set import PaperSet
from api.models.paper_set_item import PaperSetItem
from api.schemas.export import ExportCreate
from api.core.exceptions import NotFoundError, ForbiddenError
from api.core.jobs import create_job
from api.models.job import JobType


class ExportService:
    """Service for export operations"""

    async def create_export(
        self,
        db: AsyncSession,
        user_id: UUID,
        export_data: ExportCreate,
        is_admin: bool = False,
    ) -> Export:
        result = await db.execute(
            select(PaperSet).where(PaperSet.id == export_data.paper_set_id)
        )
        paper_set = result.scalar_one_or_none()

        if not paper_set:
            raise NotFoundError(detail="Paper set not found")

        if not is_admin and paper_set.user_id != user_id:
            raise ForbiddenError(detail="You don't have access to this paper set")

        export = Export(
            user_id=user_id,
            paper_set_id=export_data.paper_set_id,
            format=export_data.format,
            status=ExportStatus.PENDING.value,
        )

        db.add(export)
        await db.commit()
        await db.refresh(export)

        await create_job(
            db,
            user_id=user_id,
            job_type=JobType.EXPORT,
            payload={
                "export_id": str(export.id),
                "format": export_data.format,
            },
        )

        return export

    async def get_export_by_id(self, db: AsyncSession, export_id: UUID) -> Export:
        result = await db.execute(select(Export).where(Export.id == export_id))
        export = result.scalar_one_or_none()
        if not export:
            raise NotFoundError(detail="Export not found")
        return export

    async def list_exports(
        self,
        db: AsyncSession,
        user_id: UUID,
        is_admin: bool = False,
        skip: int = 0,
        limit: int = 20
    ) -> List[Export]:
        """列出用户的导出记录"""
        query = select(Export).order_by(Export.created_at.desc())
        if not is_admin:
            query = query.where(Export.user_id == user_id)

        result = await db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())

    async def list_exports_by_paper_set(
        self,
        db: AsyncSession,
        paper_set_id: UUID,
        user_id: UUID,
        is_admin: bool = False,
    ) -> List[Export]:
        """列出特定组卷的导出记录"""
        # 首先检查用户是否有权限访问该组卷
        result = await db.execute(
            select(PaperSet).where(PaperSet.id == paper_set_id)
        )
        paper_set = result.scalar_one_or_none()

        if not paper_set:
            raise NotFoundError(detail="Paper set not found")

        if not is_admin and paper_set.user_id != user_id:
            raise ForbiddenError(detail="You don't have access to this paper set")

        # 获取该组卷的所有导出记录
        query = select(Export).where(
            Export.paper_set_id == paper_set_id
        ).order_by(Export.created_at.desc())

        result = await db.execute(query)
        return list(result.scalars().all())

    async def build_export_items(
        self,
        db: AsyncSession,
        export_id: UUID,
        paper_set_id: UUID
    ) -> None:
        await db.execute(delete(ExportItem).where(ExportItem.export_id == export_id))

        result = await db.execute(
            select(PaperSetItem, Question, QuestionImage, Image)
            .join(Question, PaperSetItem.question_id == Question.id)
            .outerjoin(QuestionImage, QuestionImage.question_id == Question.id)
            .outerjoin(Image, QuestionImage.image_id == Image.id)
            .where(PaperSetItem.paper_set_id == paper_set_id)
            .order_by(PaperSetItem.order_index, QuestionImage.order_index)
        )

        rows = result.all()

        grouped_questions: dict[str, dict] = {}
        for paper_set_item, question, question_image, image in rows:
            question_id = str(question.id)
            if question_id not in grouped_questions:
                grouped_questions[question_id] = {
                    "paper_set_item": paper_set_item,
                    "question": question,
                    "stem_images": [],
                }

            if question_image and image:
                grouped_questions[question_id]["stem_images"].append({
                    "image_id": str(question_image.image_id),
                    "order_index": question_image.order_index,
                    "url": image.object_key,
                })

        for item in grouped_questions.values():
            paper_set_item = item["paper_set_item"]
            question = item["question"]
            snapshot = {
                "id": str(question.id),
                "type": question.type,
                "difficulty": question.difficulty,
                "stem_text": question.stem_text,
                "stem_latex": question.stem_latex,
                "appendix": question.appendix,
                "content_json": question.content_json,
                "paper_meta": question.paper_meta,
                "tags_json": question.tags_json,
                "stem_images": item["stem_images"],
                "score": float(paper_set_item.score) if paper_set_item.score else None,
                "section_title": paper_set_item.section_title,
            }

            export_item = ExportItem(
                export_id=export_id,
                question_id=question.id,
                order_index=paper_set_item.order_index,
                snapshot_json=snapshot,
            )

            db.add(export_item)

        await db.commit()

    async def delete_export(
        self,
        db: AsyncSession,
        export_id: UUID,
        user_id: UUID,
        is_admin: bool = False,
    ) -> None:
        export = await self.get_export_by_id(db, export_id)
        if not is_admin and export.user_id != user_id:
            raise ForbiddenError(detail="You don't have permission to delete this export")

        await db.delete(export)
        await db.commit()


export_service = ExportService()
