from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from api.models.submission_item import SubmissionItemResult


class SubmissionBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class SubmissionCreate(SubmissionBase):
    pass


class SubmissionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class SubmissionResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime


class SubmissionItemBase(BaseModel):
    result: SubmissionItemResult
    wrong_reason: Optional[str] = None
    note: Optional[str] = None


class SubmissionItemUpdate(SubmissionItemBase):
    pass


class SubmissionItemResponse(BaseModel):
    submission_id: UUID
    question_id: UUID
    result: SubmissionItemResult
    wrong_reason: Optional[str]
    note: Optional[str]
    updated_at: datetime


class BatchUpsertItem(BaseModel):
    question_id: UUID
    result: SubmissionItemResult
    wrong_reason: Optional[str] = None
    note: Optional[str] = None


class BatchUpsertRequest(BaseModel):
    items: List[BatchUpsertItem]
