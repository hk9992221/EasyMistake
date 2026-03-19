from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from api.models.base import BaseModel


class QuestionProgress(BaseModel):
    __tablename__ = "question_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "question_id", name="uq_question_progress_user_question"),
    )

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)

    total_attempts = Column(Integer, nullable=False, default=0)
    wrong_attempts = Column(Integer, nullable=False, default=0)
    correct_attempts = Column(Integer, nullable=False, default=0)
    consecutive_correct = Column(Integer, nullable=False, default=0)

    mastery_level = Column(Integer, nullable=False, default=1)
    proficiency_score = Column(Integer, nullable=False, default=50)
    self_assessment = Column(String(32), nullable=True)

    last_result = Column(String(16), nullable=True)
    last_reviewed_at = Column(DateTime(timezone=True), nullable=True)
    next_review_at = Column(DateTime(timezone=True), nullable=True, index=True)

    review_stage = Column(Integer, nullable=False, default=0)
    is_mastered = Column(Boolean, nullable=False, default=False, index=True)

    user = relationship("User", back_populates="question_progress")
    question = relationship("Question", back_populates="progress_records")
