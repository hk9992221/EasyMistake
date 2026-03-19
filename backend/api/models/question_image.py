from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from api.models.base import Base
from api.core.datetime_utils import utcnow


class QuestionImage(Base):
    """
    题干图片关联表，支持一个题目关联多张图片
    用于题干包含多张图片的场景（如多页题目、复合题等）
    """
    __tablename__ = "question_images"

    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    image_id = Column(UUID(as_uuid=True), ForeignKey("images.id", ondelete="RESTRICT"), nullable=False, primary_key=True)
    order_index = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # 关系
    question = relationship("Question", back_populates="images")
    image = relationship("Image")
