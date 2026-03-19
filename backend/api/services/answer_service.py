from uuid import UUID
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from api.models.answer import Answer
from api.models.answer_image import AnswerImage
from api.models.image import Image
from api.schemas.answer import AnswerUpdate


class AnswerService:
    """Service for answer operations"""

    async def get_answer_by_question_id(self, db: AsyncSession, question_id: UUID) -> Optional[Answer]:
        result = await db.execute(select(Answer).where(Answer.question_id == question_id))
        return result.scalar_one_or_none()

    async def upsert_answer(
        self,
        db: AsyncSession,
        question_id: UUID,
        answer_data: AnswerUpdate,
        updater_id: Optional[UUID] = None,
    ) -> Answer:
        result = await db.execute(select(Answer).where(Answer.question_id == question_id))
        answer = result.scalar_one_or_none()

        # 分离图片数据和其他字段
        data = answer_data.model_dump(exclude_unset=True, exclude={"images"})
        images_data = answer_data.images if hasattr(answer_data, 'images') and answer_data.images else None

        if answer:
            # 更新现有答案
            for field, value in data.items():
                setattr(answer, field, value)
            if updater_id:
                answer.updated_by = updater_id

            # 处理图片关联
            if images_data is not None:
                # 删除旧的图片关联
                await db.execute(
                    delete(AnswerImage).where(AnswerImage.question_id == question_id)
                )

                # 添加新的图片关联
                for img_item in images_data:
                    answer_image = AnswerImage(
                        question_id=question_id,
                        image_id=img_item.image_id,
                        order_index=img_item.order_index
                    )
                    db.add(answer_image)
        else:
            # 创建新答案
            answer = Answer(
                question_id=question_id,
                updated_by=updater_id,
                **data,
            )
            db.add(answer)

            # 添加图片关联
            if images_data:
                for img_item in images_data:
                    answer_image = AnswerImage(
                        question_id=question_id,
                        image_id=img_item.image_id,
                        order_index=img_item.order_index
                    )
                    db.add(answer_image)

        await db.commit()
        await db.refresh(answer)
        return answer


answer_service = AnswerService()
