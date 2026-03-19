from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from api.models.base import Base
from api.core.datetime_utils import utcnow


class ExportItem(Base):
    __tablename__ = "export_items"

    export_id = Column(UUID(as_uuid=True), ForeignKey("exports.id", ondelete="CASCADE"), primary_key=True)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="RESTRICT"), primary_key=True)
    order_index = Column(Integer, nullable=False)
    snapshot_json = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    export = relationship("Export", back_populates="items")
    question = relationship("Question", back_populates="export_items")
