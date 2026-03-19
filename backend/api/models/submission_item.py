from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from api.models.base import Base
from api.core.datetime_utils import utcnow


class SubmissionItemResult(str, enum.Enum):
    CORRECT = "CORRECT"
    WRONG = "WRONG"
    SKIPPED = "SKIPPED"


class SubmissionItem(Base):
    __tablename__ = "submission_items"

    submission_id = Column(UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="CASCADE"), primary_key=True)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True)
    result = Column(String(16), nullable=False)
    wrong_reason = Column(Text, nullable=True)
    note = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, onupdate=utcnow)

    submission = relationship("Submission", back_populates="items")
    question = relationship("Question", back_populates="submission_items")
