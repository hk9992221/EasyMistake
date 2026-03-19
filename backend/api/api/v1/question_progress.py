from math import ceil
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.deps import get_db, get_current_user
from api.models.user import User
from api.schemas.question_progress import (
    QuestionProgressCreate,
    QuestionProgressResponse,
    QuestionProgressListResponse,
    QuestionProgressUpdate,
)
from api.services.question_progress_service import question_progress_service
from api.core.exceptions import AppException


router = APIRouter(prefix="/question-progress", tags=["question-progress"])


@router.get("", response_model=QuestionProgressListResponse, include_in_schema=False)
@router.get("/", response_model=QuestionProgressListResponse)
async def list_question_progress(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    question_id: Optional[UUID] = None,
    due_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = await question_progress_service.list_progress(
        db=db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        question_id=question_id,
        due_only=due_only,
    )
    total_pages = ceil(total / page_size) if total else 0
    return QuestionProgressListResponse(
        items=[QuestionProgressResponse.model_validate(x) for x in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("", response_model=QuestionProgressResponse, status_code=201, include_in_schema=False)
@router.post("/", response_model=QuestionProgressResponse, status_code=201)
async def create_question_progress(
    payload: QuestionProgressCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    progress = await question_progress_service.create_progress(db, current_user.id, payload.question_id)
    return progress


@router.get("/{progress_id}", response_model=QuestionProgressResponse)
async def get_question_progress(
    progress_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        progress = await question_progress_service.get_progress(
            db=db,
            progress_id=progress_id,
            user_id=current_user.id,
            is_admin=current_user.role == "ADMIN",
        )
        return progress
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.patch("/{progress_id}", response_model=QuestionProgressResponse)
async def update_question_progress(
    progress_id: UUID,
    payload: QuestionProgressUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        progress = await question_progress_service.update_progress(
            db=db,
            progress_id=progress_id,
            payload=payload,
            user_id=current_user.id,
            is_admin=current_user.role == "ADMIN",
        )
        return progress
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
