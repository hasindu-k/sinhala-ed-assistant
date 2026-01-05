import enum
import uuid
from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, Text, Integer, DateTime, Enum, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.core.database import Base


class Message(Base):
    __tablename__ = "messages"
    
    class GradeLevelEnum(str, enum.Enum):
        grade_6_8 = "grade_6_8"
        grade_9_11 = "grade_9_11"
        grade_12_13 = "grade_12_13"
        university = "university"
    

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(Enum("user", "assistant", "system", name="message_role"), nullable=False)
    modality = Column(Enum("text", "voice", name="message_modality"), nullable=False, default="text")
    content = Column(Text, nullable=True)
    grade_level = Column(Enum(GradeLevelEnum), nullable=True)
    audio_url = Column(String, nullable=True)
    transcript = Column(Text, nullable=True)
    audio_duration_sec = Column(Numeric, nullable=True)
    model_name = Column(String, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    parent_msg_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship(
        "ChatSession",
        back_populates="messages"
    )

    attachments = relationship(
        "MessageAttachment",
        back_populates="message",
        cascade="all, delete-orphan"
    )

    context_chunks = relationship(
        "MessageContextChunk",
        back_populates="message",
        cascade="all, delete-orphan"
    )

    safety_reports = relationship(
        "MessageSafetyReport",
        back_populates="message",
        cascade="all, delete-orphan"
    )
