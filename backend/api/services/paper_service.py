from uuid import UUID
from typing import Callable, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from api.models.paper import Paper, PaperKind
from api.models.question import Question
from api.schemas.paper import PaperCreate, PaperUpdate
from api.core.exceptions import NotFoundError, ForbiddenError


class PaperService:
    """Service for paper/source management operations"""

    @staticmethod
    def _parse_expression(value: str) -> List[List[str]]:
        tokens = [token for token in value.split() if token]
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

    async def create_paper(
        self,
        db: AsyncSession,
        user_id: UUID,
        paper_data: PaperCreate,
    ) -> Paper:
        paper = Paper(
            user_id=user_id,
            kind=paper_data.kind,
            title=paper_data.title,
            subject=paper_data.subject,
            book_name=paper_data.book_name,
            chapter_name=paper_data.chapter_name,
            term_label=paper_data.term_label,
            grade_label=paper_data.grade_label,
            source_code=paper_data.source_code,
            source_meta=paper_data.source_meta or {},
            qr_code=paper_data.qr_code,
            qr_payload=paper_data.qr_payload,
        )

        db.add(paper)
        await db.commit()
        await db.refresh(paper)
        return paper

    async def list_papers(
        self,
        db: AsyncSession,
        user_id: UUID,
        is_admin: bool = False,
        skip: int = 0,
        limit: int = 20,
        subject: Optional[str] = None,
        kind: Optional[PaperKind] = None,
        search: Optional[str] = None,
    ) -> List[Paper]:
        query = select(Paper).order_by(Paper.created_at.desc())

        if not is_admin:
            query = query.where(Paper.user_id == user_id)

        if subject:
            query = query.where(Paper.subject == subject)

        if kind:
            query = query.where(Paper.kind == kind)

        if search:
            search_condition = self._build_expression_condition(
                search,
                lambda token: or_(
                    Paper.title.ilike(f"%{token}%"),
                    Paper.book_name.ilike(f"%{token}%"),
                    Paper.chapter_name.ilike(f"%{token}%"),
                )
            )
            if search_condition is not None:
                query = query.where(search_condition)

        result = await db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())

    async def get_paper(self, db: AsyncSession, paper_id: UUID) -> Paper:
        result = await db.execute(select(Paper).where(Paper.id == paper_id))
        paper = result.scalar_one_or_none()
        if not paper:
            raise NotFoundError(detail="Paper not found")
        return paper

    async def get_paper_by_qr_code(
        self,
        db: AsyncSession,
        qr_code: str,
    ) -> Paper:
        result = await db.execute(select(Paper).where(Paper.qr_code == qr_code))
        paper = result.scalar_one_or_none()
        if not paper:
            raise NotFoundError(detail="Paper not found")
        return paper

    async def get_paper_questions(
        self,
        db: AsyncSession,
        paper_id: UUID,
        user_id: UUID,
        is_admin: bool = False,
    ) -> List[Question]:
        # First check paper access
        paper = await self.get_paper(db, paper_id)
        if not is_admin and paper.user_id != user_id:
            raise ForbiddenError(detail="You don't have permission to access this paper")

        # Get questions for this paper
        result = await db.execute(
            select(Question)
            .where(Question.paper_id == paper_id)
            .where(Question.is_deleted == False)
            .order_by(Question.page_no, Question.question_no)
        )
        return list(result.scalars().all())

    async def update_paper(
        self,
        db: AsyncSession,
        paper_id: UUID,
        paper_data: PaperUpdate,
        user_id: UUID,
        is_admin: bool = False,
    ) -> Paper:
        paper = await self.get_paper(db, paper_id)

        if not is_admin and paper.user_id != user_id:
            raise ForbiddenError(detail="You don't have permission to update this paper")

        update_data = paper_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(paper, field, value)

        await db.commit()
        await db.refresh(paper)
        return paper

    async def delete_paper(
        self,
        db: AsyncSession,
        paper_id: UUID,
        user_id: UUID,
        is_admin: bool = False,
    ) -> None:
        paper = await self.get_paper(db, paper_id)

        if not is_admin and paper.user_id != user_id:
            raise ForbiddenError(detail="You don't have permission to delete this paper")

        await db.delete(paper)
        await db.commit()


paper_service = PaperService()
