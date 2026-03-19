from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import Field
from api.models.extraction import ExtractionStatus
from api.schemas.common import BaseSchema


class ExtractionBase(BaseSchema):
    paper_id: Optional[UUID] = None


class ExtractionCreate(ExtractionBase):
    image_ids: List[UUID] = Field(..., min_items=1)
    model_name: Optional[str] = "qwen3-vl-flash"
    params: Dict[str, Any] = Field(default_factory=dict)


class ExtractionUpdate(BaseSchema):
    pass


class ExtractionResponse(BaseSchema):
    id: UUID
    user_id: UUID
    paper_id: Optional[UUID]
    status: ExtractionStatus
    model_name: Optional[str]
    model_version: Optional[str]
    prompt_version: Optional[str]
    params: Dict[str, Any]
    raw_json: Optional[Dict[str, Any]]
    confidence: Optional[Dict[str, Any]]
    warnings: Optional[Dict[str, Any]]
    error: Optional[str]
    created_at: datetime
    updated_at: datetime


class DraftQuestion(BaseSchema):
    number: str
    problem: str
    choices: Optional[str] = None  # 选择题选项，格式 "A. xxx\nB. xxx\n..."
    appendix: Optional[str] = None  # 附录/补充材料


class DraftQuestionsResponse(BaseSchema):
    extraction_id: UUID
    questions: List[DraftQuestion]
