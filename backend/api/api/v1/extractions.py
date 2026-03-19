from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from api.core.database import get_db
from api.core.deps import get_current_user
from api.schemas.extraction import ExtractionCreate, ExtractionResponse, DraftQuestionsResponse
from api.schemas.question import QuestionCreate, QuestionResponse
from api.services.extraction_service import extraction_service
from api.services.question_service import question_service
from api.models.user import User, UserRole
from api.core.exceptions import ForbiddenError, NotFoundError


router = APIRouter(prefix="/extractions", tags=["Extractions"])


@router.post("", response_model=ExtractionResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ExtractionResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_extraction(
    extraction_data: ExtractionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_admin = current_user.role == UserRole.ADMIN
    return await extraction_service.create_extraction(db, current_user.id, extraction_data, is_admin=is_admin)


@router.get("", response_model=list[ExtractionResponse])
@router.get("/", response_model=list[ExtractionResponse], include_in_schema=False)
async def list_extractions(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_admin = current_user.role == UserRole.ADMIN
    return await extraction_service.list_extractions(db, current_user.id, is_admin=is_admin, skip=skip, limit=limit)


@router.get("/{extraction_id}", response_model=ExtractionResponse)
async def get_extraction(
    extraction_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_admin = current_user.role == UserRole.ADMIN
    extraction = await extraction_service.get_extraction(db, extraction_id)
    if not extraction:
        raise NotFoundError(detail="Extraction not found")

    if not is_admin and extraction.user_id != current_user.id:
        raise ForbiddenError(detail="You don't have permission to access this extraction")

    return extraction


@router.get("/{extraction_id}/draft-questions", response_model=DraftQuestionsResponse)
async def get_draft_questions(
    extraction_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_admin = current_user.role == UserRole.ADMIN
    extraction = await extraction_service.get_extraction(db, extraction_id)
    if not extraction:
        raise NotFoundError(detail="Extraction not found")

    if not is_admin and extraction.user_id != current_user.id:
        raise ForbiddenError(detail="You don't have permission to access this extraction")

    return await extraction_service.get_draft_questions(extraction)


@router.post("/{extraction_id}/questions", response_model=list[QuestionResponse])
async def create_questions_from_extraction(
    extraction_id: UUID,
    questions: list[QuestionCreate],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_admin = current_user.role == UserRole.ADMIN
    extraction = await extraction_service.get_extraction(db, extraction_id)
    if not extraction:
        raise NotFoundError(detail="Extraction not found")

    if not is_admin and extraction.user_id != current_user.id:
        raise ForbiddenError(detail="You don't have permission to access this extraction")

    created = []
    for question in questions:
        question.from_extraction_id = extraction_id
        created.append(await question_service.create_question(db, extraction.user_id, question))
    return created


@router.post("/{extraction_id}/retry", response_model=ExtractionResponse)
async def retry_extraction(
    extraction_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_admin = current_user.role == UserRole.ADMIN
    extraction = await extraction_service.get_extraction(db, extraction_id)
    if not extraction:
        raise NotFoundError(detail="Extraction not found")

    if not is_admin and extraction.user_id != current_user.id:
        raise ForbiddenError(detail="You don't have permission to access this extraction")

    return await extraction_service.run_extraction(db, extraction)
