import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class EvaluationSession(Base):
    __tablename__ = "evaluation_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False, index=True)
    rubric_id = Column(UUID(as_uuid=True), ForeignKey("rubrics.id"), nullable=True)
    status = Column(String, nullable=True, default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EvaluationResource(Base):
    __tablename__ = "evaluation_resources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_session_id = Column(UUID(as_uuid=True), ForeignKey("evaluation_sessions.id"), nullable=False, index=True)
    resource_id = Column(UUID(as_uuid=True), ForeignKey("resource_files.id"), nullable=False)
    role = Column(String, nullable=True)  # syllabus, question_paper, answer_script


class PaperConfig(Base):
    __tablename__ = "paper_config"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_session_id = Column(UUID(as_uuid=True), ForeignKey("evaluation_sessions.id"), nullable=False, index=True)
    total_marks = Column(Integer, nullable=True)
    total_main_questions = Column(Integer, nullable=True)
    required_questions = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
