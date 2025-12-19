# app/shared/models/chat_messages.py
import uuid
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("user_chats.chat_id"), nullable=False)
    user_id = Column(String, nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    prompt_original = Column(Text, nullable=False)
    prompt_cleaned = Column(Text, nullable=True)
    model_raw_output = Column(Text, nullable=False)
    final_output = Column(Text, nullable=False)
    safety_missing_concepts = Column(JSON, nullable=True)
    safety_extra_concepts = Column(JSON, nullable=True)
    safety_flagged_sentences = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    chat = relationship("UserChat", backref="messages")