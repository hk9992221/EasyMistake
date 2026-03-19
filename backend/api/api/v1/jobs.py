from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from api.core.database import get_db
from api.core.deps import get_current_user
from api.schemas.job import JobResponse
from api.services.job_service import job_service
from api.models.user import User, UserRole
from api.core.exceptions import ForbiddenError, NotFoundError


router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("/", response_model=list[JobResponse])
async def list_jobs(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_admin = current_user.role == UserRole.ADMIN
    return await job_service.list_jobs(db, current_user.id, is_admin=is_admin, skip=skip, limit=limit)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await job_service.get_job(db, job_id)
    if not job:
        raise NotFoundError(detail="Job not found")

    if current_user.role != UserRole.ADMIN and job.user_id != current_user.id:
        raise ForbiddenError(detail="You don't have permission to access this job")

    return job
