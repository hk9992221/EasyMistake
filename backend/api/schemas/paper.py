from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from api.models.paper import PaperKind


class PaperBase(BaseModel):
    kind: PaperKind
    title: str = Field(..., min_length=1, max_length=255)
    subject: Optional[str] = None
    book_name: Optional[str] = None
    chapter_name: Optional[str] = None
    term_label: Optional[str] = None
    grade_label: Optional[str] = None
    source_code: Optional[str] = None
    source_meta: Dict[str, Any] = Field(default_factory=dict)
    qr_code: Optional[str] = None
    qr_payload: Optional[str] = None


class PaperCreate(PaperBase):
    pass


class PaperUpdate(BaseModel):
    kind: Optional[PaperKind] = None
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    subject: Optional[str] = None
    book_name: Optional[str] = None
    chapter_name: Optional[str] = None
    term_label: Optional[str] = None
    grade_label: Optional[str] = None
    source_code: Optional[str] = None
    source_meta: Optional[Dict[str, Any]] = None
    qr_code: Optional[str] = None
    qr_payload: Optional[str] = None


class PaperResponse(BaseModel):
    id: UUID
    user_id: UUID
    kind: PaperKind
    title: str
    subject: Optional[str]
    book_name: Optional[str]
    chapter_name: Optional[str]
    term_label: Optional[str]
    grade_label: Optional[str]
    source_code: Optional[str]
    source_meta: Dict[str, Any]
    qr_code: Optional[str]
    qr_payload: Optional[str]
    created_at: datetime
    updated_at: datetime
