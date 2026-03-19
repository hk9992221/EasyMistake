from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any
from api.models.job import JobType, JobStatus
from api.schemas.common import BaseSchema


class JobBase(BaseSchema):
    type: JobType
    payload: Dict[str, Any] = {}


class JobCreate(JobBase):
    pass


class JobResponse(BaseSchema):
    id: UUID
    user_id: Optional[UUID]
    type: JobType
    payload: Dict[str, Any]
    status: JobStatus
    locked_at: Optional[datetime]
    locked_by: Optional[str]
    run_after: datetime
    attempts: int
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime
