from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from api.models.base import BaseModel
import enum


class ExtractionStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


class QuestionExtraction(BaseModel):
    __tablename__ = "question_extractions"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(32), nullable=False, default=ExtractionStatus.PENDING.value, index=True)
    model_name = Column(String(128), nullable=True)
    model_version = Column(String(64), nullable=True)
    prompt_version = Column(String(64), nullable=True)
    params = Column(JSONB, nullable=False, default=dict)
    raw_json = Column(JSONB, nullable=True)
    confidence = Column(JSONB, nullable=True)
    warnings = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)

    user = relationship("User", back_populates="extractions")
    paper = relationship("Paper", back_populates="extractions")
    images = relationship("ExtractionImage", back_populates="extraction", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="from_extraction")
