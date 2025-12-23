from pydantic import BaseModel, Field
from typing import Optional, Dict
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from enum import Enum


class EvaluationStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class EvaluationResourceRole(str, Enum):
    syllabus = "syllabus"
    question_paper = "question_paper"
    answer_script = "answer_script"


# Evaluation Session Schemas
class EvaluationSessionCreate(BaseModel):
    session_id: UUID
    rubric_id: Optional[UUID] = None


class EvaluationSessionUpdate(BaseModel):
    status: Optional[EvaluationStatus] = None
    rubric_id: Optional[UUID] = None


class EvaluationSessionResponse(BaseModel):
    id: UUID
    session_id: UUID
    rubric_id: Optional[UUID] = None
    status: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Evaluation Resource Schemas
class EvaluationResourceAttach(BaseModel):
    resource_id: UUID
    role: EvaluationResourceRole


class EvaluationResourceResponse(BaseModel):
    id: UUID
    evaluation_session_id: UUID
    resource_id: UUID
    role: Optional[str] = None

    class Config:
        from_attributes = True


# Paper Config Schemas
class PaperConfigCreate(BaseModel):
    paper_part: Optional[str] = None
    subject_name: Optional[str] = None
    medium: Optional[str] = None
    weightage: Optional[Decimal] = None
    total_main_questions: Optional[int] = None
    selection_rules: Optional[Dict[str, int]] = None


class PaperConfigUpdate(BaseModel):
    paper_part: Optional[str] = None
    subject_name: Optional[str] = None
    medium: Optional[str] = None
    weightage: Optional[Decimal] = None
    total_main_questions: Optional[int] = None
    selection_rules: Optional[Dict[str, int]] = None
    is_confirmed: Optional[bool] = None


class PaperConfigResponse(BaseModel):
    id: UUID
    evaluation_session_id: UUID
    paper_part: Optional[str] = None
    subject_name: Optional[str] = None
    medium: Optional[str] = None
    weightage: Optional[Decimal] = None
    total_main_questions: Optional[int] = None
    selection_rules: Optional[Dict[str, int]] = None
    is_confirmed: Optional[bool] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Answer Document Schemas
class AnswerDocumentCreate(BaseModel):
    resource_id: UUID
    student_identifier: Optional[str] = None


class AnswerDocumentResponse(BaseModel):
    id: UUID
    evaluation_session_id: UUID
    resource_id: UUID
    student_identifier: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Question Paper Schemas
class QuestionPaperCreate(BaseModel):
    resource_id: UUID
    extracted_text: Optional[str] = None


class QuestionPaperResponse(BaseModel):
    id: UUID
    evaluation_session_id: UUID
    resource_id: UUID
    extracted_text: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Question Schemas
class QuestionCreate(BaseModel):
    question_number: Optional[str] = None
    question_text: Optional[str] = None
    max_marks: Optional[int] = None


class QuestionResponse(BaseModel):
    id: UUID
    question_paper_id: UUID
    question_number: Optional[str] = None
    question_text: Optional[str] = None
    max_marks: Optional[int] = None

    class Config:
        from_attributes = True


# Sub Question Schemas
class SubQuestionCreate(BaseModel):
    label: Optional[str] = None
    sub_question_text: Optional[str] = None
    max_marks: Optional[int] = None


class SubQuestionResponse(BaseModel):
    id: UUID
    question_id: UUID
    label: Optional[str] = None
    sub_question_text: Optional[str] = None
    max_marks: Optional[int] = None

    class Config:
        from_attributes = True


# Evaluation Result Schemas
class EvaluationResultCreate(BaseModel):
    answer_document_id: UUID
    total_score: Optional[Decimal] = None
    overall_feedback: Optional[str] = None


class EvaluationResultResponse(BaseModel):
    id: UUID
    answer_document_id: UUID
    total_score: Optional[Decimal] = None
    overall_feedback: Optional[str] = None
    evaluated_at: datetime

    class Config:
        from_attributes = True


# Question Score Schemas
class QuestionScoreCreate(BaseModel):
    sub_question_id: UUID
    awarded_marks: Optional[Decimal] = None
    feedback: Optional[str] = None


class QuestionScoreResponse(BaseModel):
    id: UUID
    evaluation_result_id: UUID
    sub_question_id: UUID
    awarded_marks: Optional[Decimal] = None
    feedback: Optional[str] = None

    class Config:
        from_attributes = True


# Combined Evaluation Result with Details
class EvaluationResultDetail(BaseModel):
    id: UUID
    answer_document_id: UUID
    total_score: Optional[Decimal] = None
    overall_feedback: Optional[str] = None
    evaluated_at: datetime
    question_scores: list[QuestionScoreResponse] = []

    class Config:
        from_attributes = True
