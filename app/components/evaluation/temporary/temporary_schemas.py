from pydantic import BaseModel
from typing import Optional, Dict, List
from decimal import Decimal


class SubQuestion(BaseModel):
    label: str  # e.g., "a", "b", "i", "ii"
    text: str
    marks: Decimal


class MainQuestion(BaseModel):
    number: str  # e.g., "1", "2"
    text: Optional[str] = None  # Main questions usually don't have text; subquestions do
    sub_questions: List[SubQuestion]


class PaperPart(BaseModel):
    name: str  # e.g., "Part I", "Part II"
    total_main_questions: int
    required_questions: int  # Number of questions student must answer
    main_questions: List[MainQuestion]


class StudentAnswer(BaseModel):
    student_id: str  # e.g., "student1"
    answers_text: str  # Plain text of answers; system will parse answered questions from numbering


class TemporaryEvaluationInput(BaseModel):
    syllabus_text: str
    paper_parts: List[PaperPart]  # Detailed question structure
    student_answers: List[StudentAnswer]  # Answers for each student
    rubric_scores: Dict[str, float]  # e.g., {"semantic": 0.8, "coverage": 0.7, "bm25": 0.9}
    subject_name: Optional[str] = None
    medium: Optional[str] = None


class SubQuestionScore(BaseModel):
    label: str
    awarded_marks: Decimal
    feedback: str


class MainQuestionScore(BaseModel):
    number: str
    total_marks: Decimal
    awarded_marks: Decimal
    sub_scores: List[SubQuestionScore]


class PartScore(BaseModel):
    name: str
    total_marks: Decimal
    awarded_marks: Decimal
    main_scores: List[MainQuestionScore]


class StudentEvaluationOutput(BaseModel):
    student_id: str
    total_score: Decimal
    overall_feedback: str
    part_scores: List[PartScore]


class TemporaryEvaluationOutput(BaseModel):
    evaluations: List[StudentEvaluationOutput]