from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class SessionResource(Base):
    __tablename__ = "session_resources"

    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), primary_key=True, nullable=False)
    resource_id = Column(UUID(as_uuid=True), ForeignKey("resource_files.id"), primary_key=True, nullable=False)
    label = Column(String, nullable=True)