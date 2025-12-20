import uuid
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.core.database import Base


class ResourceChunk(Base):
    __tablename__ = "resource_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_id = Column(UUID(as_uuid=True), ForeignKey("resource_files.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=True)
    content = Column(Text, nullable=True)
    content_length = Column(Integer, nullable=True)
    token_count = Column(Integer, nullable=True)
    embedding = Column(Vector(768), nullable=True)
    embedding_model = Column(String, nullable=True)
    start_char = Column(Integer, nullable=True)
    end_char = Column(Integer, nullable=True)
