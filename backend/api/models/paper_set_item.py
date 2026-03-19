from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from api.models.base import Base
from api.core.datetime_utils import utcnow


class PaperSetItem(Base):
    __tablename__ = "paper_set_items"

    paper_set_id = Column(UUID(as_uuid=True), ForeignKey("paper_sets.id", ondelete="CASCADE"), primary_key=True)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="RESTRICT"), primary_key=True)
    order_index = Column(Integer, nullable=False)
    section_title = Column(String(255), nullable=True)
    score = Column(Numeric(10, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    paper_set = relationship("PaperSet", back_populates="items")
    question = relationship("Question", back_populates="paper_set_items")
