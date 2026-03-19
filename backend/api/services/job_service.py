from uuid import UUID
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from api.models.job import Job


class JobService:
    """Service for jobs"""

    async def get_job(self, db: AsyncSession, job_id: UUID) -> Job:
        result = await db.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()

    async def list_jobs(
        self,
        db: AsyncSession,
        user_id: UUID,
        is_admin: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Job]:
        query = select(Job).order_by(Job.created_at.desc())
        if not is_admin:
            query = query.where(Job.user_id == user_id)

        result = await db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())


job_service = JobService()
