from sqlalchemy import Column, String, BigInteger, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from api.models.base import BaseModel


class Image(BaseModel):
    __tablename__ = "images"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    object_key = Column(String(512), nullable=False, unique=True)
    storage_url = Column(String(1024), nullable=True)
    sha256 = Column(String(64), nullable=False, index=True)
    mime = Column(String(128), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)

    # Relationships
    user = relationship("User", back_populates="images")
