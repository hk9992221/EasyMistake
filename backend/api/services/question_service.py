import re
from uuid import UUID
from typing import Callable, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, cast, text, label, case, delete, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql.type_api import TypeEngine
from api.models.question import Question
from api.models.question_image import QuestionImage
from api.models.image import Image
from api.models.attempt import Attempt, AttemptResult
from api.schemas.question import QuestionCreate, QuestionUpdate, QuestionListParams
from api.core.exceptions import NotFoundError, ForbiddenError


class QuestionService:
    """Service for question-related operations"""

    @staticmethod
    def _parse_expression(value: str) -> List[List[str]]:
        tokens = [token for token in re.split(r"\s+", value.strip()) if token]
        groups: List[List[str]] = []
        current_group: List[str] = []

        for token in tokens:
            upper_token = token.upper()
            if upper_token == "OR":
                if current_group:
                    groups.append(current_group)
                    current_group = []
                continue
            if upper_token == "AND":
                continue
            current_group.append(token)

        if current_group:
            groups.append(current_group)
        return groups

    def _build_expression_condition(self, expression: str, token_to_condition: Callable[[str], object]):
        groups = self._parse_expression(expression)
        if not groups:
            return None

        or_conditions = []
        for group in groups:
            group_conditions = [token_to_condition(token) for token in group]
            if group_conditions:
                or_conditions.append(and_(*group_conditions))

        if not or_conditions:
            return None
        if len(or_conditions) == 1:
            return or_conditions[0]
        return or_(*or_conditions)

    async def _update_question_images(
        self,
        db: AsyncSession,
        question_id: UUID,
        image_ids: List[UUID]
    ) -> None:
        """更新题目的图片关联"""
        # 删除旧的关联
        await db.execute(
            delete(QuestionImage).where(QuestionImage.question_id == question_id)
        )

        # 创建新的关联
        if image_ids:
            for order_index, image_id in enumerate(image_ids):
                question_image = QuestionImage(
                    question_id=question_id,
                    image_id=image_id,
                    order_index=order_index
                )
                db.add(question_image)

            await db.commit()

    async def create_question(
        self,
        db: AsyncSession,
        user_id: UUID,
        question_data: QuestionCreate
    ) -> Question:
        question = Question(
            user_id=user_id,
            paper_id=question_data.paper_id,
            subject=question_data.subject,
            book_name=question_data.book_name,
            chapter_name=question_data.chapter_name,
            page_no=question_data.page_no,
            question_no=question_data.question_no,
            source_anchor=question_data.source_anchor,
            type=question_data.type,
            difficulty=question_data.difficulty,
            stem_text=question_data.stem_text,
            stem_latex=question_data.stem_latex,
            appendix=question_data.appendix,
            content_json=question_data.content_json,
            paper_meta=question_data.paper_meta,
            tags_json=question_data.tags_json,
            knowledge_points_json=question_data.knowledge_points_json,
            from_extraction_id=question_data.from_extraction_id,
        )

        db.add(question)
        await db.commit()
        await db.refresh(question)

        # 处理题干图片
        if question_data.stem_image_ids:
            await self._update_question_images(db, question.id, question_data.stem_image_ids)

        return question

    async def get_question_by_id(
        self,
        db: AsyncSession,
        question_id: UUID,
        include_deleted: bool = False,
    ) -> Optional[Question]:
        query = select(Question).where(Question.id == question_id)
        if not include_deleted:
            query = query.where(Question.is_deleted.is_(False))

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def update_question(
        self,
        db: AsyncSession,
        question_id: UUID,
        question_data: QuestionUpdate,
        user_id: UUID,
        is_admin: bool = False
    ) -> Question:
        question = await self.get_question_by_id(db, question_id, include_deleted=True)
        if not question or question.is_deleted:
            raise NotFoundError(detail="Question not found")

        if not is_admin and question.user_id != user_id:
            raise ForbiddenError(detail="You don't have permission to update this question")

        update_data = question_data.model_dump(exclude_unset=True)

        # 处理题干图片更新
        if "stem_image_ids" in update_data:
            image_ids = update_data.pop("stem_image_ids")
            await self._update_question_images(db, question_id, image_ids)

        for field, value in update_data.items():
            setattr(question, field, value)

        await db.commit()
        await db.refresh(question)
        return question

    async def delete_question(
        self,
        db: AsyncSession,
        question_id: UUID,
        user_id: UUID,
        is_admin: bool = False
    ) -> None:
        question = await self.get_question_by_id(db, question_id, include_deleted=True)
        if not question or question.is_deleted:
            raise NotFoundError(detail="Question not found")

        if not is_admin and question.user_id != user_id:
            raise ForbiddenError(detail="You don't have permission to delete this question")

        question.is_deleted = True
        await db.commit()

    async def list_questions(
        self,
        db: AsyncSession,
        user_id: UUID,
        params: QuestionListParams,
        is_admin: bool = False,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[List[Question], int]:
        conditions = []

        if not is_admin:
            conditions.append(Question.user_id == user_id)

        if params.subject:
            subject_condition = self._build_expression_condition(
                params.subject,
                lambda token: Question.subject.op("~*")(re.escape(token)),
            )
            if subject_condition is not None:
                conditions.append(subject_condition)

        if params.book_name:
            book_name_condition = self._build_expression_condition(
                params.book_name,
                lambda token: Question.book_name.op("~*")(re.escape(token)),
            )
            if book_name_condition is not None:
                conditions.append(book_name_condition)

        if params.chapter_name:
            chapter_name_condition = self._build_expression_condition(
                params.chapter_name,
                lambda token: Question.chapter_name.op("~*")(re.escape(token)),
            )
            if chapter_name_condition is not None:
                conditions.append(chapter_name_condition)

        if params.paper_id:
            conditions.append(Question.paper_id == params.paper_id)
        if params.page_no:
            conditions.append(Question.page_no == params.page_no)

        if params.question_no:
            question_no_condition = self._build_expression_condition(
                params.question_no,
                lambda token: Question.question_no.op("~*")(re.escape(token)),
            )
            if question_no_condition is not None:
                conditions.append(question_no_condition)

        if params.type:
            conditions.append(Question.type == params.type)
        if params.difficulty:
            conditions.append(Question.difficulty == params.difficulty)
        if params.tags_json:
            for tag in params.tags_json:
                conditions.append(Question.tags_json.contains([tag]))
        if params.knowledge_point_q:
            knowledge_condition = self._build_expression_condition(
                params.knowledge_point_q,
                lambda token: cast(Question.knowledge_points_json, String).op("~*")(re.escape(token)),
            )
            if knowledge_condition is not None:
                conditions.append(knowledge_condition)

        if params.q:
            search_condition = self._build_expression_condition(
                params.q,
                lambda token: or_(
                    Question.stem_text.op("~*")(re.escape(token)),
                    Question.stem_latex.op("~*")(re.escape(token)),
                    Question.appendix.op("~*")(re.escape(token)),
                ),
            )
            if search_condition is not None:
                conditions.append(search_condition)

        if params.start_date:
            conditions.append(Question.created_at >= params.start_date)
        if params.end_date:
            conditions.append(Question.created_at <= params.end_date)

        conditions.append(Question.is_deleted.is_(False))

        query = select(Question).where(and_(*conditions))

        count_query = select(func.count(Question.id)).where(and_(*conditions))
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        questions = result.scalars().all()

        return list(questions), total

    async def get_user_common_tags(
        self,
        db: AsyncSession,
        user_id: UUID,
        limit: int = 4
    ) -> List[str]:
        """获取用户最常用的tag"""
        # 对于 JSONB 类型，使用 jsonb_array_elements_text 函数
        unnested_tags = func.jsonb_array_elements_text(Question.tags_json).label("tag")

        query = (
            select(unnested_tags)
            .where(Question.user_id == user_id)
            .where(Question.is_deleted.is_(False))
            .where(Question.tags_json.isnot(None))
            .group_by("tag")
            .order_by(func.count("tag").desc())
            .limit(limit)
        )

        result = await db.execute(query)
        tags = [row[0] for row in result.fetchall() if row[0]]
        return tags


question_service = QuestionService()
