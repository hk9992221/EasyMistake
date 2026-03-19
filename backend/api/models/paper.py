from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from api.models.base import BaseModel
import enum


class PaperKind(str, enum.Enum):
    EXAM_PAPER = "EXAM_PAPER"
    BOOK = "BOOK"
    WORKBOOK = "WORKBOOK"
    HANDOUT = "HANDOUT"
    OTHER = "OTHER"


class Paper(BaseModel):
    __tablename__ = "papers"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    kind = Column(String(32), nullable=False)
    title = Column(String(255), nullable=False)
    subject = Column(String(64), nullable=True, index=True)
    book_name = Column(String(255), nullable=True)
    chapter_name = Column(String(255), nullable=True)
    term_label = Column(String(128), nullable=True)
    grade_label = Column(String(64), nullable=True)
    source_code = Column(String(128), nullable=True)
    source_meta = Column(JSONB, nullable=False, default=dict)
    qr_code = Column(String(255), nullable=True, index=True)
    qr_payload = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="papers")
    questions = relationship("Question", back_populates="paper")
    extractions = relationship("QuestionExtraction", back_populates="paper")
