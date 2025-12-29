from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from decimal import Decimal


class QuestionPaperCreate(BaseModel):
    evaluation_session_id: UUID
    resource_id: UUID
    extracted_text: Optional[str] = None


class QuestionCreate(BaseModel):
    question_paper_id: UUID
    question_number: Optional[str] = None
    question_text: str
    max_marks: int


class SubQuestionCreate(BaseModel):
    question_id: UUID
    label: Optional[str] = None
    sub_question_text: str
    max_marks: int


class SubQuestionResponse(BaseModel):
    id: UUID
    question_id: UUID
    label: Optional[str]
    sub_question_text: str
    max_marks: int

    class Config:
        from_attributes = True


class QuestionResponse(BaseModel):
    id: UUID
    question_paper_id: UUID
    question_number: Optional[str]
    question_text: str
    max_marks: int
    sub_questions: Optional[List[SubQuestionResponse]] = []

    class Config:
        from_attributes = True


class QuestionPaperResponse(BaseModel):
    id: UUID
    evaluation_session_id: UUID
    resource_id: UUID
    extracted_text: Optional[str]
    created_at: datetime
    questions: Optional[List[QuestionResponse]] = []

    class Config:
        from_attributes = True
