from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, update
from api.models.job import Job, JobType, JobStatus
from typing import Dict, Any, Optional
from api.core.datetime_utils import utcnow


async def create_job(
    db: AsyncSession,
    user_id: Optional[UUID],
    job_type: JobType,
    payload: Dict[str, Any],
    run_after: Optional[datetime] = None,
    commit: bool = True,
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
    await db.flush()
    if commit:
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

    query = query.order_by(Job.run_after, Job.created_at, Job.id).with_for_update(skip_locked=True).limit(1)

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
    job.locked_at = None
    job.locked_by = None

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
    job.locked_at = None
    job.locked_by = None

    await db.commit()
    await db.refresh(job)

    return job


async def require_job_lease(db, job_id, worker_id):
    row = (await db.execute(select(Job.status, Job.locked_by).where(Job.id == job_id).with_for_update())).one_or_none()
    if row is None or row.status != JobStatus.RUNNING.value or row.locked_by != worker_id:
        raise RuntimeError("Job lease lost")


async def heartbeat_job(db, job_id, worker_id):
    result = await db.execute(update(Job).where(
        Job.id == job_id, Job.status == JobStatus.RUNNING.value, Job.locked_by == worker_id,
    ).values(locked_at=utcnow()))
    await db.commit()
    return result.rowcount == 1


async def recover_stale_jobs(db):
    from api.core.config import settings
    from api.models.extraction import QuestionExtraction
    from api.models.export import Export
    cutoff = utcnow() - timedelta(seconds=settings.JOB_LEASE_TIMEOUT_SECONDS)
    jobs = (await db.execute(select(Job).where(
        Job.status == JobStatus.RUNNING.value,
        Job.type.in_([JobType.EXPORT.value, JobType.EXTRACTION.value]),
        or_(Job.locked_at < cutoff, and_(Job.locked_at.is_(None), Job.updated_at < cutoff)),
    ).with_for_update(skip_locked=True).limit(100))).scalars().all()
    for job in jobs:
        model, key = (Export, "export_id") if job.type == JobType.EXPORT.value else (QuestionExtraction, "extraction_id")
        resource = None
        try:
            resource_id = UUID(str(job.payload[key]))
            resource = (await db.execute(select(model).where(model.id == resource_id).with_for_update())).scalar_one_or_none()
        except (ValueError, TypeError, KeyError):
            pass
        if resource is not None and resource.status == "DONE":
            job.status = JobStatus.DONE.value
            job.last_error = None
        else:
            message = "Worker interrupted; retry this task to continue"
            job.status = JobStatus.FAILED.value
            job.last_error = message
            if resource is not None:
                resource.status = "FAILED"
                resource.error = message
                if isinstance(resource, Export):
                    resource.finished_at = utcnow()
        job.locked_at = None
        job.locked_by = None
    if jobs:
        await db.commit()
    return len(jobs)
