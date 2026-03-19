from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from api.models.base import BaseModel
from api.core.datetime_utils import utcnow
import enum


class AttemptResult(str, enum.Enum):
    CORRECT = "CORRECT"
    WRONG = "WRONG"
    PARTIAL = "PARTIAL"
    SKIPPED = "SKIPPED"


class Attempt(BaseModel):
    __tablename__ = "attempts"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    result = Column(String(16), nullable=False)
    duration_sec = Column(Integer, nullable=True)
    source = Column(String(64), nullable=True)
    review_mode = Column(String(64), nullable=True)
    error_tags_json = Column(JSONB, nullable=False, default=list)
    wrong_reason = Column(Text, nullable=True)
    note = Column(Text, nullable=True)
    occurred_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    submitted_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    user = relationship("User", back_populates="attempts")
    question = relationship("Question", back_populates="attempts")

    @property
    def error_tags(self) -> list[str]:
        return self.error_tags_json or []
