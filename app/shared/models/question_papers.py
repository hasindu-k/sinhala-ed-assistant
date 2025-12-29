# app/shared/models/question_papers.py

import uuid
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class QuestionPaper(Base):
    __tablename__ = "question_papers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=True, index=True)
    evaluation_session_id = Column(UUID(as_uuid=True), ForeignKey("evaluation_sessions.id"), nullable=True, index=True)
    resource_id = Column(UUID(as_uuid=True), ForeignKey("resource_files.id"), nullable=False)
    extracted_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Question(Base):
    __tablename__ = "questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_paper_id = Column(UUID(as_uuid=True), ForeignKey("question_papers.id"), nullable=False, index=True)
    question_number = Column(String, nullable=True)
    question_text = Column(Text, nullable=True)
    max_marks = Column(Integer, nullable=True)
    shared_stem = Column(Text, nullable=True)
    inherits_shared_stem_from = Column(String, nullable=True)


class SubQuestion(Base):
    __tablename__ = "sub_questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("questions.id"),
        nullable=False,
        index=True
    )

    parent_sub_question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sub_questions.id"),
        nullable=True,
        index=True
    )

    label = Column(String, nullable=True)          # a, b, i, ii
    sub_question_text = Column(Text, nullable=True)
    max_marks = Column(Integer, nullable=True)
