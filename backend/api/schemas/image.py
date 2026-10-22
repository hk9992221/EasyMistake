from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ImageBase(BaseModel):
    sha256: str
    mime: str
    size_bytes: int
    width: Optional[int] = None
    height: Optional[int] = None


class ImageCreate(BaseModel):
    # Metadata is derived from the stored bytes, never trusted from the client.
    object_key: str = Field(min_length=1, max_length=512)


class ImageUpdate(BaseModel):
    pass


class ImageResponse(BaseModel):
    id: UUID
    user_id: UUID
    object_key: str
    storage_url: Optional[str]
    sha256: str
    mime: str
    size_bytes: int
    width: Optional[int]
    height: Optional[int]
    created_at: datetime
    updated_at: datetime


class UploadUrlResponse(BaseModel):
    upload_url: str
    object_key: str


class ImageUploadUrlRequest(BaseModel):
    filename: str
    content_type: str
    size_bytes: int = Field(gt=0)
