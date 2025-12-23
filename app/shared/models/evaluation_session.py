import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
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
    
    # Identity
    paper_part = Column(String, nullable=True)  # e.g., 'Paper_I', 'Paper_II'
    subject_name = Column(String, nullable=True)
    medium = Column(String, nullable=True)
    
    # Scoring Logic (Crucial for calculation)
    weightage = Column(Numeric(5, 2), nullable=True)  # How much this paper contributes to final grade (e.g., 40.0% or 60.0%)
    
    # Selection Rules (Needed to validate if student answered enough questions)
    total_main_questions = Column(Integer, nullable=True)
    selection_rules = Column(JSONB, nullable=True)  # Rules for valid submission, e.g., {'Part_II': 4, 'Part_III': 1}
    
    is_confirmed = Column(Boolean, nullable=True, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
