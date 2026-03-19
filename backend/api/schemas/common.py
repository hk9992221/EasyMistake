from uuid import UUID
from datetime import datetime
from typing import Optional, TypeVar, Generic
from pydantic import BaseModel, ConfigDict


T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        protected_namespaces=(),
    )


class TimestampsSchema(BaseSchema):
    """Schema with timestamp fields"""
    id: UUID
    created_at: datetime
    updated_at: datetime


class PaginationParams(BaseSchema):
    """Pagination parameters"""
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseSchema, Generic[T]):
    """Generic paginated response"""
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class MessageResponse(BaseSchema):
    """Simple message response"""
    message: str
