from sqlalchemy import Column, String, Float, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from api.models.base import BaseModel


class GradingRecord(BaseModel):
    __tablename__ = "grading_records"
    __table_args__ = (CheckConstraint("score >= 0 AND score <= 150", name="ck_grading_score"),)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    student_name = Column(String(50), nullable=False)
    paper_name = Column(String(80), nullable=False)
    score = Column(Float, nullable=False)
    comment = Column(String(200), nullable=False, default="")
