# app/shared/models/resource_data.py
import uuid
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class ResourceData(Base):
    __tablename__ = "resource_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("user_chats.chat_id"), nullable=False)
    user_id = Column(String, nullable=False)
    resource_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    chat = relationship("UserChat", backref="resources")