from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from api.models.base import BaseModel
from api.core.datetime_utils import utcnow
import enum


class JobType(str, enum.Enum):
    EXTRACTION = "EXTRACTION"
    ANSWER_GENERATION = "ANSWER_GENERATION"
    EXPORT = "EXPORT"


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


class Job(BaseModel):
    __tablename__ = "jobs"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    type = Column(String(32), nullable=False)
    payload = Column(JSONB, nullable=False, default=dict)
    status = Column(String(32), nullable=False, default=JobStatus.PENDING.value)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    locked_by = Column(String(128), nullable=True)
    run_after = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)

    user = relationship("User", back_populates="jobs")
