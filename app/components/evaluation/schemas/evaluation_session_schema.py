from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID
from enum import Enum


class EvaluationStatusEnum(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class ResourceRoleEnum(str, Enum):
    syllabus = "syllabus"
    question_paper = "question_paper"
    answer_script = "answer_script"


class PaperConfigCreate(BaseModel):
    total_marks: int
    total_main_questions: int
    required_questions: int


class PaperConfigResponse(BaseModel):
    id: UUID
    evaluation_session_id: UUID
    total_marks: int
    total_main_questions: int
    required_questions: int
    created_at: datetime

    class Config:
        from_attributes = True


class EvaluationSessionCreate(BaseModel):
    session_id: UUID
    rubric_id: Optional[UUID] = None
    status: EvaluationStatusEnum = EvaluationStatusEnum.pending


class EvaluationSessionUpdate(BaseModel):
    status: Optional[EvaluationStatusEnum] = None
    rubric_id: Optional[UUID] = None


class EvaluationSessionResponse(BaseModel):
    id: UUID
    session_id: UUID
    rubric_id: Optional[UUID]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
