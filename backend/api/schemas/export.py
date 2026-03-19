from uuid import UUID
from datetime import datetime
from typing import Optional
from api.models.export import ExportFormat, ExportStatus
from api.schemas.common import BaseSchema


class ExportBase(BaseSchema):
    paper_set_id: UUID
    format: ExportFormat


class ExportCreate(ExportBase):
    pass


class ExportResponse(BaseSchema):
    id: UUID
    user_id: UUID
    paper_set_id: UUID
    format: ExportFormat
    status: ExportStatus
    object_key: Optional[str]
    size_bytes: Optional[int]
    sha256: Optional[str]
    error: Optional[str]
    created_at: datetime
    updated_at: datetime
    finished_at: Optional[datetime]


class DownloadUrlResponse(BaseSchema):
    download_url: str
    expires_at: datetime
