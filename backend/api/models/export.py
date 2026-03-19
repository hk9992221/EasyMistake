from datetime import datetime
from sqlalchemy import Column, String, BigInteger, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from api.models.base import BaseModel
import enum


class ExportFormat(str, enum.Enum):
    MARKDOWN_ZIP = "MARKDOWN_ZIP"
    LATEX_ZIP = "LATEX_ZIP"


class ExportStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


class Export(BaseModel):
    __tablename__ = "exports"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    paper_set_id = Column(UUID(as_uuid=True), ForeignKey("paper_sets.id", ondelete="SET NULL"), nullable=True)
    format = Column(String(32), nullable=True)
    status = Column(String(32), nullable=False, default=ExportStatus.PENDING.value)
    object_key = Column(String(512), nullable=True)
    size_bytes = Column(BigInteger, nullable=True)
    sha256 = Column(String(64), nullable=True)
    error = Column(String, nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="exports")
    paper_set = relationship("PaperSet", back_populates="exports")
    items = relationship("ExportItem", back_populates="export", cascade="all, delete-orphan")
