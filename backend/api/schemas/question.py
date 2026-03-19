from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import Field
from api.models.question import QuestionType, DifficultyLevel
from api.schemas.common import BaseSchema


class QuestionImageItem(BaseSchema):
    """题干图片项"""
    image_id: UUID
    order_index: int
    url: Optional[str] = None


class QuestionBase(BaseSchema):
    subject: Optional[str] = None
    book_name: Optional[str] = None
    chapter_name: Optional[str] = None
    page_no: Optional[int] = None
    question_no: Optional[str] = None
    source_anchor: Optional[str] = None
    type: QuestionType
    difficulty: Optional[DifficultyLevel] = None
    stem_text: Optional[str] = None
    stem_latex: Optional[str] = None
    appendix: Optional[str] = None
    content_json: Dict[str, Any] = Field(default_factory=dict)
    paper_meta: Dict[str, Any] = Field(default_factory=dict)
    tags_json: List[str] = Field(default_factory=list)
    knowledge_points_json: List[str] = Field(default_factory=list)
    # 题干图片ID列表
    stem_image_ids: List[UUID] = Field(default_factory=list)


class QuestionCreate(QuestionBase):
    paper_id: Optional[UUID] = None
    from_extraction_id: Optional[UUID] = None


class QuestionUpdate(BaseSchema):
    subject: Optional[str] = None
    book_name: Optional[str] = None
    chapter_name: Optional[str] = None
    page_no: Optional[int] = None
    question_no: Optional[str] = None
    source_anchor: Optional[str] = None
    type: Optional[QuestionType] = None
    difficulty: Optional[DifficultyLevel] = None
    stem_text: Optional[str] = None
    stem_latex: Optional[str] = None
    appendix: Optional[str] = None
    content_json: Optional[Dict[str, Any]] = None
    paper_meta: Optional[Dict[str, Any]] = None
    tags_json: Optional[List[str]] = None
    knowledge_points_json: Optional[List[str]] = None
    # 题干图片ID列表
    stem_image_ids: Optional[List[UUID]] = None


class QuestionResponse(BaseSchema):
    id: UUID
    user_id: UUID
    created_by: Optional[str] = None
    paper_id: Optional[UUID]
    subject: Optional[str]
    book_name: Optional[str]
    chapter_name: Optional[str]
    page_no: Optional[int]
    question_no: Optional[str]
    source_anchor: Optional[str]
    type: QuestionType
    difficulty: Optional[DifficultyLevel]
    stem_text: Optional[str]
    stem_latex: Optional[str]
    appendix: Optional[str]  # 添加appendix字段
    content_json: Dict[str, Any]
    paper_meta: Dict[str, Any]
    tags_json: List[str]
    knowledge_points_json: List[str] = Field(default_factory=list)
    from_extraction_id: Optional[UUID]
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    # 题干图片列表
    stem_images: List[QuestionImageItem] = Field(default_factory=list)


class QuestionListParams(BaseSchema):
    subject: Optional[str] = None
    book_name: Optional[str] = None
    chapter_name: Optional[str] = None
    paper_id: Optional[UUID] = None
    page_no: Optional[int] = None
    question_no: Optional[str] = None
    type: Optional[QuestionType] = None
    difficulty: Optional[DifficultyLevel] = None
    tags_json: Optional[List[str]] = None
    knowledge_point_q: Optional[str] = None
    q: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
