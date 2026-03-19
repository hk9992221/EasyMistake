from datetime import datetime, date
from uuid import UUID
from api.schemas.common import BaseSchema


class ReviewQueueItem(BaseSchema):
    question_id: UUID
    progress_id: UUID
    priority: int
    reason: str
    review_stage: int
    next_review_at: datetime | None
    proficiency_score: int


class ReviewQueueResponse(BaseSchema):
    date: date
    items: list[ReviewQueueItem]
