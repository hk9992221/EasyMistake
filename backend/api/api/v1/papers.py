from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.deps import get_db, get_current_user
from api.models.user import User
from api.models.paper import PaperKind
from api.schemas.paper import PaperCreate, PaperUpdate, PaperResponse
from api.schemas.question import QuestionResponse
from api.services.paper_service import paper_service
from api.core.exceptions import AppException

router = APIRouter()


@router.post("/papers", response_model=PaperResponse, status_code=201)
async def create_paper(
    paper_data: PaperCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建新的整卷/资料源"""
    try:
        is_admin = current_user.role == "ADMIN"
        paper = await paper_service.create_paper(db, current_user.id, paper_data)
        return paper
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.get("/papers", response_model=List[PaperResponse])
async def list_papers(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    subject: Optional[str] = None,
    kind: Optional[PaperKind] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取整卷/资料源列表（支持筛选和搜索）"""
    is_admin = current_user.role == "ADMIN"
    papers = await paper_service.list_papers(
        db,
        current_user.id,
        is_admin=is_admin,
        skip=skip,
        limit=limit,
        subject=subject,
        kind=kind,
        search=search,
    )
    return papers


@router.get("/papers/{paper_id}", response_model=PaperResponse)
async def get_paper(
    paper_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取整卷/资料源详情"""
    try:
        is_admin = current_user.role == "ADMIN"
        paper = await paper_service.get_paper(db, paper_id)

        # Check access permission
        if not is_admin and paper.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="You don't have permission to access this paper")

        return paper
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.get("/papers/by-qr/{qr_code}", response_model=PaperResponse)
async def get_paper_by_qr_code(
    qr_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """通过二维码获取整卷/资料源"""
    try:
        is_admin = current_user.role == "ADMIN"
        paper = await paper_service.get_paper_by_qr_code(db, qr_code)

        # Check access permission
        if not is_admin and paper.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="You don't have permission to access this paper")

        return paper
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.get("/papers/{paper_id}/questions", response_model=List[QuestionResponse])
async def get_paper_questions(
    paper_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取整卷/资料源关联的题目列表"""
    try:
        is_admin = current_user.role == "ADMIN"
        questions = await paper_service.get_paper_questions(
            db,
            paper_id,
            current_user.id,
            is_admin=is_admin,
        )
        return questions
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.patch("/papers/{paper_id}", response_model=PaperResponse)
async def update_paper(
    paper_id: UUID,
    paper_data: PaperUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新整卷/资料源信息"""
    try:
        is_admin = current_user.role == "ADMIN"
        paper = await paper_service.update_paper(
            db,
            paper_id,
            paper_data,
            current_user.id,
            is_admin=is_admin,
        )
        return paper
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.delete("/papers/{paper_id}", status_code=204)
async def delete_paper(
    paper_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除整卷/资料源"""
    try:
        is_admin = current_user.role == "ADMIN"
        await paper_service.delete_paper(
            db,
            paper_id,
            current_user.id,
            is_admin=is_admin,
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
