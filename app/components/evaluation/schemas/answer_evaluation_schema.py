from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from decimal import Decimal


class QuestionScoreCreate(BaseModel):
    evaluation_result_id: UUID
    sub_question_id: UUID
    awarded_marks: Decimal
    feedback: Optional[str] = None


class QuestionScoreResponse(BaseModel):
    id: UUID
    evaluation_result_id: UUID
    sub_question_id: UUID
    awarded_marks: Optional[Decimal]
    feedback: Optional[str]

    class Config:
        from_attributes = True


class EvaluationResultCreate(BaseModel):
    answer_document_id: UUID
    total_score: Optional[Decimal] = None
    overall_feedback: Optional[str] = None


class EvaluationResultUpdate(BaseModel):
    total_score: Optional[Decimal] = None
    overall_feedback: Optional[str] = None


class EvaluationResultResponse(BaseModel):
    id: UUID
    answer_document_id: UUID
    total_score: Optional[Decimal]
    overall_feedback: Optional[str]
    evaluated_at: datetime
    question_scores: Optional[List[QuestionScoreResponse]] = []

    class Config:
        from_attributes = True


class AnswerDocumentCreate(BaseModel):
    evaluation_session_id: UUID
    resource_id: UUID
    student_identifier: Optional[str] = None


class AnswerDocumentResponse(BaseModel):
    id: UUID
    evaluation_session_id: UUID
    resource_id: UUID
    student_identifier: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
