from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from api.models.job import Job, JobType, JobStatus
from typing import Dict, Any, Optional
from api.core.datetime_utils import utcnow


async def create_job(
    db: AsyncSession,
    user_id: Optional[UUID],
    job_type: JobType,
    payload: Dict[str, Any],
    run_after: Optional[datetime] = None,
) -> Job:
    """Create a new job"""
    if run_after is None:
        run_after = utcnow()

    job = Job(
        user_id=user_id,
        type=job_type.value,
        payload=payload,
        status=JobStatus.PENDING.value,
        run_after=run_after,
    )

    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def fetch_next_job(
    db: AsyncSession,
    worker_id: str,
    job_types: Optional[list[JobType]] = None,
) -> Optional[Job]:
    """Fetch next available job for processing"""
    query = select(Job).where(
        and_(
            Job.status == JobStatus.PENDING.value,
            Job.run_after <= utcnow(),
        )
    )

    if job_types:
        type_values = [job_type.value for job_type in job_types]
        query = query.where(Job.type.in_(type_values))

    query = query.with_for_update(skip_locked=True).limit(1)

    result = await db.execute(query)
    job = result.scalar_one_or_none()

    if not job:
        return None

    job.status = JobStatus.RUNNING.value
    job.locked_at = utcnow()
    job.locked_by = worker_id
    job.attempts += 1

    await db.commit()
    await db.refresh(job)

    return job


async def complete_job(
    db: AsyncSession,
    job_id: UUID,
    success: bool = True,
    error: Optional[str] = None,
) -> Job:
    """Mark job as completed or failed"""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise ValueError("Job not found")

    job.status = JobStatus.DONE.value if success else JobStatus.FAILED.value
    job.last_error = error

    await db.commit()
    await db.refresh(job)

    return job


async def retry_job(
    db: AsyncSession,
    job_id: UUID,
    delay_seconds: int = 60,
) -> Job:
    """Retry a failed job"""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise ValueError("Job not found")

    job.status = JobStatus.PENDING.value
    job.run_after = utcnow() + timedelta(seconds=delay_seconds)
    job.last_error = None

    await db.commit()
    await db.refresh(job)

    return job
