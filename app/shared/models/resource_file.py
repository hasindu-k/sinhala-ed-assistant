import uuid
from sqlalchemy import Column, String, Integer, DateTime, Enum, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class ResourceFile(Base):
    __tablename__ = "resource_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    original_filename = Column(String, nullable=True)
    storage_path = Column(String, nullable=True)
    mime_type = Column(String, nullable=True)
    size_bytes = Column(BigInteger, nullable=True)
    source_type = Column(Enum("user_upload", "url", "system", name="resource_source"), nullable=True)
    language = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
