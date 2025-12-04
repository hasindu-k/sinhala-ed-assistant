# app/components/evaluation/schemas/evaluation_schema.py

from pydantic import BaseModel, Field
from typing import List, Dict, Optional


# ------------------------------------------------------------
# 1. UPLOAD SCHEMAS (teacher uploads once)
# ------------------------------------------------------------

class SyllabusUpload(BaseModel):
    user_id: str
    syllabus_chunks: List[str]


class QuestionUpload(BaseModel):
    user_id: str
    questions: Dict[str, str]   # {"Q01_a": "...", "Q01_b": "..."}


class RubricUpload(BaseModel):
    user_id: str
    semantic_weight: float = Field(..., ge=0, le=1)
    coverage_weight: float = Field(..., ge=0, le=1)
    bm25_weight: float = Field(..., ge=0, le=1)


class MarksUpload(BaseModel):
    user_id: str
    marks_distribution: List[int]


    class Config:
        arbitrary_types_allowed = True
   # Example: [3,3,6,8]


class PaperSettingsUpload(BaseModel):
    user_id: str
    total_marks: int                       # Full paper = e.g. 60
    total_main_questions: int             # e.g. 5
    required_main_questions: int          # e.g. 3
    subquestions_per_main: int            # e.g. 4

class OCRProcessedUpload(BaseModel):
    user_id: str
    raw_text: str
    total_main_questions: int
    sub_questions_per_main: int

class PaperUpload(BaseModel):
    user_id: str
    raw_text: str
    total_main_questions: int
    sub_questions_per_main: int


# ------------------------------------------------------------
# 2. MAIN EVALUATION INPUT (student only)
# ------------------------------------------------------------

class EvaluationRequest(BaseModel):
    user_id: str
    student_answers: Dict[str, str]       # {"Q01_a": "...", ...}
    language: Optional[str] = "sinhala"   # sinhala | english | both


# ------------------------------------------------------------
# 3. INTERNAL OUTPUT STRUCTURES
# ------------------------------------------------------------

class SubQuestionResult(BaseModel):
    question_id: str
    student_answer: str
    retrieved_context: List[str]

    semantic_score: float
    coverage_score: float
    bm25_score: float

    allocated_marks: float                 # from marks_distribution
    total_score: float                     # student achieved
    max_score: float                       # allocated marks

    feedback: str                          # AI-generated feedback


class MainQuestionResult(BaseModel):
    main_question_id: str
    sub_results: List[SubQuestionResult]
    question_total: float
    question_max: float


# ------------------------------------------------------------
# 4. FINAL RESPONSE (TO FRONTEND)
# ------------------------------------------------------------

class FinalEvaluationResponse(BaseModel):
    results: Dict[str, SubQuestionResult]   # subquestion-by-subquestion
    selected_main_questions: List[str]      # best required main questions

    final_score_obtained: float
    final_score_total: float

    overall_feedback: Optional[str]
    per_question_feedback: Dict[str, str]
