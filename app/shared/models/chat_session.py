# app/shared/models/chat_session.py

import uuid
from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, Integer, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    mode = Column(Enum("learning", "evaluation", name="chat_mode"), nullable=False, default="learning")
    channel = Column(Enum("text", "voice", "mixed", name="chat_channel"), nullable=False, default="text")
    title = Column(String, nullable=True)
    description = Column(String, nullable=True)
    grade = Column(Integer, nullable=True)
    subject = Column(String, nullable=True)
    rubric_id = Column(UUID(as_uuid=True), ForeignKey("rubrics.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    messages = relationship(
        "Message", 
        back_populates="session", 
        cascade="all, delete-orphan" 
    )

    resources = relationship(
        "SessionResource",
        backref="session",
        cascade="all, delete-orphan"
    )

    @property
    def question_paper(self):
        if self.mode != "evaluation":
            return None
        for res in self.resources:
            if res.label == "question_paper":
                return {
                    "id": res.resource_id, 
                    "resource_id": res.resource_id,
                    "filename": res.resource.original_filename if res.resource else None
                }
        return None

    @property
    def syllabus(self):
        if self.mode != "evaluation":
            return None
        for res in self.resources:
            if res.label == "syllabus":
                return {
                    "id": res.resource_id, 
                    "resource_id": res.resource_id,
                    "filename": res.resource.original_filename if res.resource else None
                }
        return None
