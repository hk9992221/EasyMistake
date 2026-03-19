from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from api.models.base import Base
from api.core.datetime_utils import utcnow


class AnswerImage(Base):
    """
    答案图片关联表，支持一个答案关联多张图片
    """
    __tablename__ = "answer_images"

    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    image_id = Column(UUID(as_uuid=True), ForeignKey("images.id", ondelete="RESTRICT"), nullable=False, primary_key=True)
    order_index = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # 关系
    # 明确指定关联条件，因为 answer_images.question_id 外键指向 questions.id
    answer = relationship(
        "Answer",
        back_populates="images",
        primaryjoin="AnswerImage.question_id == Answer.question_id",
        foreign_keys="AnswerImage.question_id"
    )
    image = relationship("Image")
