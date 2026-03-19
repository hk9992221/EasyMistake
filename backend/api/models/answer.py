from sqlalchemy import Column, String, Text, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from api.models.base import BaseModel
import enum


class AnswerType(str, enum.Enum):
    NONE = "NONE"
    TEXT = "TEXT"
    LATEX = "LATEX"
    IMAGE = "IMAGE"
    MIXED = "MIXED"


class Answer(BaseModel):
    __tablename__ = "answers"

    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, unique=True, index=True, primary_key=True)
    answer_type = Column(String(16), nullable=False, default=AnswerType.NONE.value)
    answer_text = Column(Text, nullable=True)
    answer_latex = Column(Text, nullable=True)
    explanation_text = Column(Text, nullable=True)
    explanation_latex = Column(Text, nullable=True)
    content_json = Column(JSONB, nullable=False, default=dict)

    from_extraction_id = Column(UUID(as_uuid=True), ForeignKey("question_extractions.id", ondelete="SET NULL"), nullable=True)
    from_api_call_id = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    question = relationship("Question", back_populates="answer")
    updater = relationship("User", foreign_keys=[updated_by])

    # 明确指定关联条件，因为 answer_images.question_id 外键指向 questions.id 而不是 answers.question_id
    images = relationship(
        "AnswerImage",
        back_populates="answer",
        primaryjoin="Answer.question_id == AnswerImage.question_id",
        foreign_keys="[AnswerImage.question_id]",
        cascade="all, delete-orphan"
    )
