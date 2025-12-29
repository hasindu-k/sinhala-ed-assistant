# app/shared/models/message.py

import uuid
from sqlalchemy import Column, String, Text, Integer, DateTime, Enum, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.core.database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(Enum("user", "assistant", "system", name="message_role"), nullable=False)
    modality = Column(Enum("text", "voice", name="message_modality"), nullable=False, default="text")
    content = Column(Text, nullable=True)
    grade_level = Column(Enum("6 - 8", "9 - 11", "12 - 13", "university", name="grade_level"), nullable=True)
    audio_url = Column(String, nullable=True)
    transcript = Column(Text, nullable=True)
    audio_duration_sec = Column(Numeric, nullable=True)
    model_name = Column(String, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
