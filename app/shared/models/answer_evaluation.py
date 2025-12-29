import uuid
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class AnswerDocument(Base):
    __tablename__ = "answer_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_session_id = Column(UUID(as_uuid=True), ForeignKey("evaluation_sessions.id"), nullable=False, index=True)
    resource_id = Column(UUID(as_uuid=True), ForeignKey("resource_files.id"), nullable=False)
    student_identifier = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    answer_document_id = Column(UUID(as_uuid=True), ForeignKey("answer_documents.id"), nullable=False, index=True)
    total_score = Column(Numeric, nullable=True)
    overall_feedback = Column(Text, nullable=True)
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now())


class QuestionScore(Base):
    __tablename__ = "question_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_result_id = Column(UUID(as_uuid=True), ForeignKey("evaluation_results.id"), nullable=False, index=True)
    sub_question_id = Column(UUID(as_uuid=True), ForeignKey("sub_questions.id"), nullable=False)
    awarded_marks = Column(Numeric, nullable=True)
    feedback = Column(Text, nullable=True)
