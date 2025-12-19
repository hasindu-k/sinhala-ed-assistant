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
    questions: Dict[str, str]  # {"Q01_a": "...", "Q01_b": "..."}


class RubricUpload(BaseModel):
    user_id: str
    semantic_weight: float = Field(..., ge=0, le=1)
    coverage_weight: float = Field(..., ge=0, le=1)
    bm25_weight: float = Field(..., ge=0, le=1)


class MarksUpload(BaseModel):
    """
    DEPRECATED: Use PaperStructureUpload instead.
    Kept only for backward compatibility during migration.
    """
    user_id: str
    marks_distribution: List[int]


class PaperSettingsUpload(BaseModel):
    user_id: str
    total_marks: int
    total_main_questions: int
    required_main_questions: int


class OCRProcessedUpload(BaseModel):
    user_id: str
    raw_text: str
    total_main_questions: int
    sub_questions_per_main: int  # preview/legacy only


class PaperUpload(BaseModel):
    user_id: str
    raw_text: str
    total_main_questions: int
    sub_questions_per_main: int  # legacy only


class AnswerUpload(BaseModel):
    user_id: str
    raw_text: str


# --- NEW: Paper Structure Schemas ---
class SubQuestionSchema(BaseModel):
    text: str
    marks: float


class MainQuestionSchema(BaseModel):
    total_marks: float
    subquestions: Dict[str, SubQuestionSchema]  # "a": {text, marks}


class PaperStructureSchema(BaseModel):
    main_questions: Dict[str, MainQuestionSchema]  # "1": {...}


class PaperStructureUpload(BaseModel):
    user_id: str
    paper_structure: PaperStructureSchema


# ------------------------------------------------------------
# 2. MAIN EVALUATION INPUT (student only)
# ------------------------------------------------------------
class EvaluationRequest(BaseModel):
    user_id: str
    student_answers: Dict[str, Dict[str, str]]  # {"1": {"a": "..."}, ...}
    language: Optional[str] = "sinhala"  # sinhala | english | both


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

    allocated_marks: float
    total_score: float
    max_score: float

    feedback: str


class MainQuestionResult(BaseModel):
    main_question_id: str
    sub_results: List[SubQuestionResult]
    question_total: float
    question_max: float
    selected: bool = False


# ------------------------------------------------------------
# 4. FINAL RESPONSE (TO FRONTEND)
# ------------------------------------------------------------
class FinalEvaluationResponse(BaseModel):
    results: Dict[str, SubQuestionResult]
    main_questions: Dict[str, MainQuestionResult]

    selected_main_questions: List[str]
    ignored_main_questions: List[str]

    final_score_obtained: float
    final_score_total: float

    overall_feedback: Optional[str]
    per_question_feedback: Dict[str, str]
