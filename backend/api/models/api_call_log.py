from sqlalchemy import Column, String, Text, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from api.models.base import BaseModel
from sqlalchemy import ForeignKey


class ApiCallLog(BaseModel):
    __tablename__ = "api_call_logs"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    purpose = Column(String(64), nullable=False)
    provider = Column(String(64), nullable=True)
    model_name = Column(String(128), nullable=True)
    request_json = Column(JSONB, nullable=False, default=dict)
    response_json = Column(JSONB, nullable=False, default=dict)
    usage_json = Column(JSONB, nullable=False, default=dict)
    cost_usd = Column(Numeric(18, 8), nullable=False, default=0)
    pricing_version = Column(String(64), nullable=True)
    status_code = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)
    latency_ms = Column(Integer, nullable=True)
