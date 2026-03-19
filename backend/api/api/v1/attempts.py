from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.deps import get_db, get_current_user
from api.models.user import User
from api.models.attempt import AttemptResult
from api.schemas.attempt import AttemptCreate, AttemptUpdate, AttemptResponse
from api.schemas.question import QuestionResponse
from api.services.attempt_service import attempt_service
from api.core.exceptions import AppException

router = APIRouter()


@router.post("/attempts", response_model=AttemptResponse, status_code=201)
async def create_attempt(
    attempt_data: AttemptCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """记录做题结果"""
    try:
        attempt = await attempt_service.create_attempt(db, current_user.id, attempt_data)
        return attempt
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.post("/question-attempts", response_model=AttemptResponse, status_code=201)
async def create_question_attempt(
    attempt_data: AttemptCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        attempt = await attempt_service.create_attempt(db, current_user.id, attempt_data)
        return attempt
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.get("/attempts", response_model=List[AttemptResponse])
async def list_attempts(
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=100),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    question_id: Optional[UUID] = None,
    result: Optional[AttemptResult] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取做题记录列表（支持筛选）"""
    if page is not None or page_size is not None:
        p = page or 1
        ps = page_size or 20
        skip = (p - 1) * ps
        limit = ps

    is_admin = current_user.role == "ADMIN"
    attempts = await attempt_service.list_attempts(
        db,
        current_user.id,
        is_admin=is_admin,
        skip=skip,
        limit=limit,
        question_id=question_id,
        result=result,
    )
    return attempts


@router.get("/question-attempts", response_model=List[AttemptResponse])
async def list_question_attempts(
    question_id: Optional[UUID] = None,
    result: Optional[AttemptResult] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attempts = await attempt_service.list_attempts(
        db,
        current_user.id,
        is_admin=current_user.role == "ADMIN",
        skip=(page - 1) * page_size,
        limit=page_size,
        question_id=question_id,
        result=result,
    )
    return attempts


@router.get("/questions/{question_id}/attempts", response_model=List[AttemptResponse])
async def get_question_attempts(
    question_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取特定题目的所有做题记录"""
    attempts = await attempt_service.get_user_attempts_for_question(
        db,
        current_user.id,
        question_id,
    )
    return attempts


@router.get("/attempts/mistakes/analysis")
async def get_mistakes_analysis(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取错题分析（包含错题和做题记录）"""
    mistakes = await attempt_service.get_mistakes_analysis(
        db,
        current_user.id,
        skip=skip,
        limit=limit,
    )

    # Format response
    response_data = []
    for item in mistakes:
        attempt = item["attempt"]
        question = item["question"]

        response_data.append({
            "attempt": AttemptResponse.model_validate(attempt),
            "question": QuestionResponse.model_validate(question),
        })

    return response_data


@router.get("/attempts/stats")
async def get_attempt_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取做题统计（总作答、总错题、未掌握错题）"""
    return await attempt_service.get_attempt_stats(db, current_user.id)


@router.get("/attempts/{attempt_id}", response_model=AttemptResponse)
async def get_attempt(
    attempt_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取做题记录详情"""
    try:
        is_admin = current_user.role == "ADMIN"
        attempt = await attempt_service.get_attempt(db, attempt_id)

        # Check access permission
        if not is_admin and attempt.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="You don't have permission to access this attempt")

        return attempt
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.get("/question-attempts/{attempt_id}", response_model=AttemptResponse)
async def get_question_attempt(
    attempt_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_attempt(attempt_id=attempt_id, db=db, current_user=current_user)


@router.patch("/attempts/{attempt_id}", response_model=AttemptResponse)
async def update_attempt(
    attempt_id: UUID,
    attempt_data: AttemptUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新做题记录（修改错因、备注等）"""
    try:
        is_admin = current_user.role == "ADMIN"
        attempt = await attempt_service.update_attempt(
            db,
            attempt_id,
            attempt_data,
            current_user.id,
            is_admin=is_admin,
        )
        return attempt
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.post("/question-attempts/{attempt_id}/error-tags", response_model=AttemptResponse)
async def set_attempt_error_tags(
    attempt_id: UUID,
    tags: List[str],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payload = AttemptUpdate(error_tags=tags)
    return await update_attempt(attempt_id=attempt_id, attempt_data=payload, db=db, current_user=current_user)


@router.delete("/attempts/{attempt_id}", status_code=204)
async def delete_attempt(
    attempt_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除做题记录"""
    try:
        is_admin = current_user.role == "ADMIN"
        await attempt_service.delete_attempt(
            db,
            attempt_id,
            current_user.id,
            is_admin=is_admin,
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
