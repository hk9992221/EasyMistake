from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import Field
from api.models.answer import AnswerType
from api.schemas.common import BaseSchema


class AnswerImageItem(BaseSchema):
    """答案图片项"""
    image_id: UUID
    order_index: int
    url: Optional[str] = None  # 图片URL，仅在响应时填充


class AnswerBase(BaseSchema):
    answer_type: AnswerType = AnswerType.NONE
    answer_text: Optional[str] = None
    answer_latex: Optional[str] = None
    explanation_text: Optional[str] = None
    explanation_latex: Optional[str] = None
    content_json: Dict[str, Any] = Field(default_factory=dict)
    images: Optional[List[AnswerImageItem]] = None


class AnswerCreate(AnswerBase):
    pass


class AnswerUpdate(AnswerBase):
    pass


class AnswerResponse(BaseSchema):
    question_id: UUID
    answer_type: AnswerType
    answer_text: Optional[str]
    answer_latex: Optional[str]
    explanation_text: Optional[str]
    explanation_latex: Optional[str]
    content_json: Dict[str, Any]
    images: List[AnswerImageItem] = Field(default_factory=list)
    from_extraction_id: Optional[UUID]
    from_api_call_id: Optional[UUID]
    updated_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
