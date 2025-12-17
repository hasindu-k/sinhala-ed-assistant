import uuid
from sqlalchemy import Column, String, Text, Integer, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    sender = Column(Enum("user", "assistant", "system", name="sender_enum"), nullable=False)
    message = Column(Text, nullable=True)
    tokens_used = Column(Integer, default=0)
    audio_url = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)
    file_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
