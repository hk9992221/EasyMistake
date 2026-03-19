import re
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, cast, String
from api.core.database import get_db
from api.core.deps import get_current_user
from api.schemas.paper_set import (
    PaperSetCreate,
    PaperSetUpdate,
    PaperSetResponse,
    PaperSetItemCreate,
    PaperSetItemUpdate,
    PaperSetItemResponse,
    PaperSetPreviewResponse,
    BatchUpsertPaperSetRequest,
)
from api.schemas.common import PaginatedResponse
from api.services.paper_set_service import paper_set_service
from api.models.user import User, UserRole
from api.models.paper_set import PaperSet
from api.models.paper_set_item import PaperSetItem
from api.core.exceptions import ForbiddenError, NotFoundError


router = APIRouter(prefix="/paper-sets", tags=["PaperSets"])


def _parse_expression(value: str) -> list[list[str]]:
    tokens = [token for token in value.split() if token]
    groups: list[list[str]] = []
    current_group: list[str] = []

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


def _build_expression_condition(expression: str, token_to_condition):
    groups = _parse_expression(expression)
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


@router.post("", response_model=PaperSetResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/", response_model=PaperSetResponse, status_code=status.HTTP_201_CREATED)
async def create_paper_set(
    paper_set_data: PaperSetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await paper_set_service.create_paper_set(db, current_user.id, paper_set_data)


@router.get("", response_model=None, include_in_schema=False)
@router.get("/", response_model=None)
async def list_paper_sets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Search by id or title"),
    name_regex: str | None = Query(None, description="Regex pattern for paper set title"),
    start_date: datetime | None = Query(None, description="Filter created_at >= start_date"),
    end_date: datetime | None = Query(None, description="Filter created_at <= end_date"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_admin = current_user.role == UserRole.ADMIN
    skip = (page - 1) * page_size

    if name_regex:
        try:
            re.compile(name_regex)
        except re.error:
            raise HTTPException(status_code=422, detail="Invalid regex pattern in name_regex")

    # Build base query
    base_query = select(PaperSet)
    if not is_admin:
        base_query = base_query.where(PaperSet.user_id == current_user.id)

    if start_date:
        base_query = base_query.where(PaperSet.created_at >= start_date)
    if end_date:
        base_query = base_query.where(PaperSet.created_at <= end_date)

    if search:
        search_condition = _build_expression_condition(
            search,
            lambda token: or_(
                PaperSet.title.ilike(f"%{token}%"),
                cast(PaperSet.id, String).ilike(f"%{token}%"),
            ),
        )
        if search_condition is not None:
            base_query = base_query.where(search_condition)

    if name_regex:
        base_query = base_query.where(PaperSet.title.op("~*")(name_regex))

    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Get paginated paper sets
    query = base_query.order_by(PaperSet.created_at.desc()).offset(skip).limit(page_size)
    paper_sets_result = await db.execute(query)
    paper_sets = list(paper_sets_result.scalars().all())

    # Get question counts for each paper set
    from api.models.paper_set_item import PaperSetItem
    paper_set_ids = [ps.id for ps in paper_sets]

    if paper_set_ids:
        # Query to count items for each paper set
        item_counts_query = select(
            PaperSetItem.paper_set_id,
            func.count(PaperSetItem.question_id).label('count')
        ).where(
            PaperSetItem.paper_set_id.in_(paper_set_ids)
        ).group_by(PaperSetItem.paper_set_id)

        item_counts_result = await db.execute(item_counts_query)
        item_counts = {row.paper_set_id: row.count for row in item_counts_result}
    else:
        item_counts = {}

    # Convert to dict with item_count included
    items = []
    for ps in paper_sets:
        item = {
            "id": str(ps.id),
            "user_id": str(ps.user_id),
            "title": ps.title,
            "subject": ps.subject,
            "description": ps.description,
            "output_format": ps.output_format.value if hasattr(ps.output_format, 'value') else str(ps.output_format),
            "render_options": ps.render_options,
            "item_count": item_counts.get(ps.id, 0),
            "created_at": ps.created_at.isoformat() if ps.created_at else None,
            "updated_at": ps.updated_at.isoformat() if ps.updated_at else None,
        }
        items.append(item)

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/{paper_set_id}", response_model=PaperSetResponse)
async def get_paper_set(
    paper_set_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_admin = current_user.role == UserRole.ADMIN
    paper_set = await paper_set_service.get_paper_set(db, paper_set_id)
    if not paper_set:
        raise NotFoundError(detail="Paper set not found")

    if not is_admin and paper_set.user_id != current_user.id:
        raise ForbiddenError(detail="You don't have permission to access this paper set")

    return paper_set


@router.get("/{paper_set_id}/items", response_model=list[PaperSetItemResponse])
async def list_paper_set_items(
    paper_set_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_admin = current_user.role == UserRole.ADMIN
    paper_set = await paper_set_service.get_paper_set(db, paper_set_id)
    if not paper_set:
        raise NotFoundError(detail="Paper set not found")

    if not is_admin and paper_set.user_id != current_user.id:
        raise ForbiddenError(detail="You don't have permission to access this paper set")

    result = await db.execute(
        select(PaperSetItem)
        .where(PaperSetItem.paper_set_id == paper_set_id)
        .order_by(PaperSetItem.order_index)
    )
    return list(result.scalars().all())


@router.patch("/{paper_set_id}", response_model=PaperSetResponse)
async def update_paper_set(
    paper_set_id: UUID,
    paper_set_data: PaperSetUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_admin = current_user.role == UserRole.ADMIN
    return await paper_set_service.update_paper_set(
        db,
        paper_set_id,
        paper_set_data,
        current_user.id,
        is_admin=is_admin,
    )


@router.delete("/{paper_set_id}")
async def delete_paper_set(
    paper_set_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_admin = current_user.role == UserRole.ADMIN
    await paper_set_service.delete_paper_set(db, paper_set_id, current_user.id, is_admin=is_admin)
    return {"message": "Paper set deleted successfully"}


@router.put("/{paper_set_id}/items/{question_id}", response_model=PaperSetItemResponse)
async def upsert_paper_set_item(
    paper_set_id: UUID,
    question_id: UUID,
    item_data: PaperSetItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_admin = current_user.role == UserRole.ADMIN
    return await paper_set_service.upsert_item(
        db,
        paper_set_id,
        question_id,
        item_data,
        current_user.id,
        is_admin=is_admin,
    )


@router.patch("/{paper_set_id}/items/{question_id}", response_model=PaperSetItemResponse)
async def update_paper_set_item(
    paper_set_id: UUID,
    question_id: UUID,
    item_data: PaperSetItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_admin = current_user.role == UserRole.ADMIN
    return await paper_set_service.update_item(
        db,
        paper_set_id,
        question_id,
        item_data,
        current_user.id,
        is_admin=is_admin,
    )


@router.delete("/{paper_set_id}/items/{question_id}")
async def delete_paper_set_item(
    paper_set_id: UUID,
    question_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_admin = current_user.role == UserRole.ADMIN
    await paper_set_service.delete_item(db, paper_set_id, question_id, current_user.id, is_admin=is_admin)
    return {"message": "Item deleted successfully"}


@router.post("/{paper_set_id}/items/batch", response_model=list[PaperSetItemResponse])
async def batch_upsert_items(
    paper_set_id: UUID,
    request: BatchUpsertPaperSetRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_admin = current_user.role == UserRole.ADMIN
    return await paper_set_service.batch_upsert_items(
        db,
        paper_set_id,
        request,
        current_user.id,
        is_admin=is_admin,
    )


@router.get("/{paper_set_id}/preview", response_model=PaperSetPreviewResponse)
async def preview_paper_set(
    paper_set_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_admin = current_user.role == UserRole.ADMIN
    return await paper_set_service.preview_paper_set(db, paper_set_id, current_user.id, is_admin=is_admin)
