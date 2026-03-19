from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from api.models.base import BaseModel
import enum


class OutputFormat(str, enum.Enum):
    MARKDOWN = "MARKDOWN"
    LATEX = "LATEX"


class PaperSet(BaseModel):
    __tablename__ = "paper_sets"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    subject = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)
    output_format = Column(String(32), nullable=False, default=OutputFormat.MARKDOWN.value)
    render_options = Column(JSONB, nullable=False, default=dict)

    user = relationship("User", back_populates="paper_sets")
    items = relationship("PaperSetItem", back_populates="paper_set", cascade="all, delete-orphan")
    exports = relationship(
        "Export",
        back_populates="paper_set",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
