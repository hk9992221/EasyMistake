from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import Field
from api.models.paper_set import OutputFormat
from api.schemas.common import BaseSchema


class PaperSetBase(BaseSchema):
    title: str = Field(..., min_length=1, max_length=255)
    subject: Optional[str] = None
    description: Optional[str] = None
    output_format: OutputFormat = OutputFormat.MARKDOWN
    render_options: Dict[str, Any] = Field(default_factory=dict)


class PaperSetCreate(PaperSetBase):
    pass


class PaperSetUpdate(BaseSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    subject: Optional[str] = None
    description: Optional[str] = None
    output_format: Optional[OutputFormat] = None
    render_options: Optional[Dict[str, Any]] = None


class PaperSetResponse(BaseSchema):
    id: UUID
    user_id: UUID
    title: str
    subject: Optional[str] = None
    description: Optional[str] = None
    output_format: OutputFormat
    render_options: Dict[str, Any] = Field(default_factory=dict)
    item_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaperSetItemCreate(BaseSchema):
    question_id: UUID
    order_index: int = Field(..., ge=0)  # Non-negative
    section_title: Optional[str] = None
    score: Optional[float] = Field(None, ge=0, le=9999.99)  # Valid range


class PaperSetItemUpdate(BaseSchema):
    order_index: Optional[int] = Field(None, ge=0)  # Non-negative
    section_title: Optional[str] = None
    score: Optional[float] = Field(None, ge=0, le=9999.99)  # Valid range


class PaperSetItemResponse(BaseSchema):
    paper_set_id: UUID
    question_id: UUID
    order_index: int
    section_title: Optional[str]
    score: Optional[float]
    created_at: datetime


class PreviewQuestion(BaseSchema):
    id: UUID
    order_index: int
    section_title: Optional[str]
    score: Optional[float]
    subject: Optional[str]
    book_name: Optional[str]
    chapter_name: Optional[str]
    page_no: Optional[int]
    question_no: Optional[str]
    source_anchor: Optional[str]
    type: str
    stem_text: Optional[str]
    stem_latex: Optional[str]
    appendix: Optional[str]
    content_json: Dict[str, Any]


class PaperSetPreviewResponse(BaseSchema):
    paper_set_id: UUID
    title: str
    subject: Optional[str]
    description: Optional[str]
    output_format: OutputFormat
    questions: List[PreviewQuestion]


class BatchUpsertPaperSetItem(BaseSchema):
    question_id: UUID
    order_index: int
    section_title: Optional[str] = None
    score: Optional[float] = None


class BatchUpsertPaperSetRequest(BaseSchema):
    items: List[BatchUpsertPaperSetItem]
