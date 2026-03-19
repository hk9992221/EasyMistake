from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import Field
from api.models.attempt import AttemptResult
from api.schemas.common import BaseSchema


class AttemptBase(BaseSchema):
    result: AttemptResult
    duration_sec: Optional[int] = Field(default=None, ge=0)
    source: Optional[str] = None
    review_mode: Optional[str] = None
    error_tags: List[str] = Field(default_factory=list)
    wrong_reason: Optional[str] = None
    note: Optional[str] = None


class AttemptCreate(AttemptBase):
    question_id: UUID
    occurred_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None


class AttemptUpdate(BaseSchema):
    result: Optional[AttemptResult] = None
    duration_sec: Optional[int] = Field(default=None, ge=0)
    source: Optional[str] = None
    review_mode: Optional[str] = None
    error_tags: Optional[List[str]] = None
    wrong_reason: Optional[str] = None
    note: Optional[str] = None
    submitted_at: Optional[datetime] = None


class AttemptResponse(BaseSchema):
    id: UUID
    user_id: UUID
    question_id: UUID
    result: AttemptResult
    duration_sec: Optional[int]
    source: Optional[str]
    review_mode: Optional[str]
    error_tags: List[str]
    wrong_reason: Optional[str]
    note: Optional[str]
    occurred_at: datetime
    submitted_at: datetime
    created_at: datetime
    updated_at: datetime
