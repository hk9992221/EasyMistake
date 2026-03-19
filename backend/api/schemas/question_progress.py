from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import Field
from api.schemas.common import BaseSchema, PaginatedResponse


class QuestionProgressUpdate(BaseSchema):
    self_assessment: Optional[str] = None
    next_review_at: Optional[datetime] = None


class QuestionProgressCreate(BaseSchema):
    question_id: UUID


class QuestionProgressResponse(BaseSchema):
    id: UUID
    user_id: UUID
    question_id: UUID
    total_attempts: int
    wrong_attempts: int
    correct_attempts: int
    consecutive_correct: int
    mastery_level: int
    proficiency_score: int
    self_assessment: Optional[str]
    last_result: Optional[str]
    last_reviewed_at: Optional[datetime]
    next_review_at: Optional[datetime]
    review_stage: int
    is_mastered: bool
    created_at: datetime
    updated_at: datetime


class QuestionProgressListResponse(PaginatedResponse[QuestionProgressResponse]):
    pass


class ReviewCompleteRequest(BaseSchema):
    result: str = Field(pattern="^(CORRECT|WRONG|PARTIAL|SKIPPED)$")
    duration_sec: Optional[int] = Field(default=None, ge=0)
    error_tags: list[str] = Field(default_factory=list)
    note: Optional[str] = None
