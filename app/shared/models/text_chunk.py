# app/shared/models/text_chunk.py
import uuid
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class TextChunk(Base):
    __tablename__ = "text_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_id = Column(UUID(as_uuid=True), ForeignKey("resource_data.id"), nullable=False)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("user_chats.chat_id"), nullable=False)
    user_id = Column(String, nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Order of chunk in resource
    content = Column(Text, nullable=False)
    content_length = Column(Integer, nullable=False)
    
    # For BM25 index
    tokens = Column(JSONB, nullable=True)  # Tokenized Sinhala words
    
    # For semantic index
    embedding = Column(JSONB, nullable=True)  # Vector embedding
    embedding_model = Column(String, nullable=True)
    
    # Metadata
    lesson_numbers = Column(JSONB, nullable=True)  # Extracted lesson numbers
    key_phrases = Column(JSONB, nullable=True)  # Extracted key phrases
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    resource = relationship("ResourceData", backref="chunks")
    chat = relationship("UserChat", backref="chunks")

    def __repr__(self):
        return f"<TextChunk(id={self.id}, chunk_index={self.chunk_index}, length={self.content_length})>"