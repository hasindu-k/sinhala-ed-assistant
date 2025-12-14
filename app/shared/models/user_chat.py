# app/shared/models/user_chats.py
import uuid
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.database import Base


class UserChat(Base):
    __tablename__ = "user_chats"

    chat_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False)
    title = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())