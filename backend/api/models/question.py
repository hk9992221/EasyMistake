from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from api.models.base import BaseModel
import enum


class QuestionType(str, enum.Enum):
    MCQ = "MCQ"
    FILL_BLANK = "FILL_BLANK"
    SHORT_ANSWER = "SHORT_ANSWER"
    COMPUTATION = "COMPUTATION"
    PROOF = "PROOF"
    OTHER = "OTHER"


class DifficultyLevel(str, enum.Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class Question(BaseModel):
    __tablename__ = "questions"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id", ondelete="SET NULL"), nullable=True)

    # Classification
    subject = Column(String(64), nullable=True, index=True)
    book_name = Column(String(255), nullable=True, index=True)
    chapter_name = Column(String(255), nullable=True)

    # Location
    page_no = Column(Integer, nullable=True, index=True)
    question_no = Column(String(64), nullable=True, index=True)
    source_anchor = Column(String(255), nullable=True)

    # Content
    type = Column(String(32), nullable=False)
    difficulty = Column(String(32), nullable=True)
    stem_text = Column(Text, nullable=True)
    stem_latex = Column(Text, nullable=True)
    appendix = Column(Text, nullable=True)  # 附录/补充材料
    content_json = Column(JSONB, nullable=False, default=dict)

    # Metadata
    paper_meta = Column(JSONB, nullable=False, default=dict)
    tags_json = Column(JSONB, nullable=False, default=list)
    knowledge_points_json = Column(JSONB, nullable=False, default=list)

    # Source tracking
    from_extraction_id = Column(UUID(as_uuid=True), ForeignKey("question_extractions.id", ondelete="SET NULL"), nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)

    # Relationships
    user = relationship("User", back_populates="questions")
    paper = relationship("Paper", back_populates="questions")
    from_extraction = relationship("QuestionExtraction", back_populates="questions")
    images = relationship("QuestionImage", back_populates="question", cascade="all, delete-orphan")
    answer = relationship("Answer", back_populates="question", uselist=False, cascade="all, delete-orphan")
    attempts = relationship("Attempt", back_populates="question", cascade="all, delete-orphan")
    progress_records = relationship("QuestionProgress", back_populates="question", cascade="all, delete-orphan")
    submission_items = relationship("SubmissionItem", back_populates="question", cascade="all, delete-orphan")
    paper_set_items = relationship("PaperSetItem", back_populates="question", cascade="all, delete-orphan")
    export_items = relationship("ExportItem", back_populates="question", cascade="all, delete-orphan")
