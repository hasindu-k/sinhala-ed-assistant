# app/shared/models/answer_evaluation.py

import uuid
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Numeric, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class AnswerDocument(Base):
    __tablename__ = "answer_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_session_id = Column(UUID(as_uuid=True), ForeignKey("evaluation_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_id = Column(UUID(as_uuid=True), ForeignKey("resource_files.id", ondelete="CASCADE"), nullable=False)
    student_identifier = Column(String, nullable=True)
    mapped_answers = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    evaluation_session = relationship("EvaluationSession", backref="answer_documents")


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    answer_document_id = Column(UUID(as_uuid=True), ForeignKey("answer_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    total_score = Column(Numeric, nullable=True)
    overall_feedback = Column(Text, nullable=True)
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now())

    answer_document = relationship("AnswerDocument", backref="evaluation_results")




class StudentAnswer(Base):
    __tablename__ = "student_answers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    answer_document_id = Column(UUID(as_uuid=True), ForeignKey("answer_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id"), nullable=True)
    sub_question_id = Column(UUID(as_uuid=True), ForeignKey("sub_questions.id"), nullable=True)
    answer_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    answer_document = relationship("AnswerDocument", backref="student_answers")
    question = relationship("Question", foreign_keys=[question_id])
    sub_question = relationship("SubQuestion", foreign_keys=[sub_question_id])


class QuestionScore(Base):
    __tablename__ = "question_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_result_id = Column(UUID(as_uuid=True), ForeignKey("evaluation_results.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id"), nullable=True)
    sub_question_id = Column(UUID(as_uuid=True), ForeignKey("sub_questions.id"), nullable=True)
    awarded_marks = Column(Numeric, nullable=True)
    feedback = Column(Text, nullable=True)
    student_answer = Column(Text, nullable=True)

    question = relationship("Question", foreign_keys=[question_id])
    sub_question = relationship("SubQuestion", foreign_keys=[sub_question_id])


class MarkingReference(Base):
    __tablename__ = "marking_references"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_session_id = Column(UUID(as_uuid=True), ForeignKey("evaluation_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id"), nullable=True)
    sub_question_id = Column(UUID(as_uuid=True), ForeignKey("sub_questions.id"), nullable=True)
    
    question_number = Column(String, nullable=True)
    question_text = Column(Text, nullable=True)
    reference_answer = Column(Text, nullable=True)
    is_approved = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    evaluation_session = relationship("EvaluationSession", backref="marking_references")
    question = relationship("Question", foreign_keys=[question_id])
    sub_question = relationship("SubQuestion", foreign_keys=[sub_question_id])
