from datetime import datetime, date
from uuid import UUID
from api.schemas.common import BaseSchema
from api.schemas.question import QuestionResponse
from api.schemas.answer import AnswerResponse
from pydantic import Field


class ReviewQueueItem(BaseSchema):
    question_id: UUID
    progress_id: UUID
    priority: int
    reason: str
    review_stage: int
    next_review_at: datetime | None
    proficiency_score: int
    question: QuestionResponse | None = None
    answer: AnswerResponse | None = None


class ReviewQueueResponse(BaseSchema):
    date: date
    items: list[ReviewQueueItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    subjects: list[str] = Field(default_factory=list)


class DailyReviewPaperSetRequest(BaseSchema):
    subject: str | None = Field(None, min_length=1, max_length=64)


class DailyReviewPaperSetResponse(BaseSchema):
    paper_set_id: UUID
    title: str
    item_count: int
    reused: bool
