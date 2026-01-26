# app/shared/models/question_papers.py

import uuid
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, and_
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, backref

from app.core.database import Base

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

    question_type = Column(String, nullable=True)  # e.g., 'essay', 'short', 'mcq', 'structured'
    correct_answer = Column(String, nullable=True)  # For MCQ/short answer

    sub_questions = relationship("SubQuestion", back_populates="question", cascade="all, delete-orphan")

    root_sub_questions = relationship(
        "SubQuestion",
        primaryjoin="and_(Question.id==SubQuestion.question_id, SubQuestion.parent_sub_question_id.is_(None))",
        viewonly=True,
        order_by="SubQuestion.label"
    )


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
    question_type = Column(String, nullable=True)  # e.g., 'essay', 'short', 'mcq', 'structured'
    correct_answer = Column(String, nullable=True)  # For MCQ/short answer

    question = relationship("Question", back_populates="sub_questions")

    children = relationship("SubQuestion", 
        backref=backref("parent", remote_side=[id]),
        cascade="all, delete-orphan"
    )
