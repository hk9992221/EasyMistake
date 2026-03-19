from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from api.models.base import Base
from api.core.datetime_utils import utcnow


class ExtractionImage(Base):
    __tablename__ = "extraction_images"

    extraction_id = Column(UUID(as_uuid=True), ForeignKey("question_extractions.id", ondelete="CASCADE"), primary_key=True)
    image_id = Column(UUID(as_uuid=True), ForeignKey("images.id", ondelete="RESTRICT"), primary_key=True)
    order_index = Column(Integer, nullable=False)
    page_no = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    extraction = relationship("QuestionExtraction", back_populates="images")
