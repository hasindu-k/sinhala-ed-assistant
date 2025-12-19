from fastapi import APIRouter
from uuid import UUID
from app.schemas.evaluation import (
    EvaluationSessionCreate,
    PaperConfigCreate,
    AnswerDocumentCreate
)

router = APIRouter()


@router.post("/sessions")
def create_evaluation_session(payload: EvaluationSessionCreate):
    """
    Start a new evaluation session with a rubric.
    """
    pass


@router.get("/sessions/{evaluation_id}")
def get_evaluation_session(evaluation_id: UUID):
    """
    Get evaluation session details.
    """
    pass


@router.post("/sessions/{evaluation_id}/resources")
def attach_evaluation_resource(
    evaluation_id: UUID,
    resource_id: UUID,
    role: str
):
    """
    Attach syllabus / question paper / answer script.
    """
    pass


@router.post("/sessions/{evaluation_id}/parse-paper")
def parse_question_paper(evaluation_id: UUID):
    """
    Extract question structure from question paper.
    """
    pass


@router.post("/sessions/{evaluation_id}/paper-config")
def save_paper_config(evaluation_id: UUID, payload: PaperConfigCreate):
    """
    Save paper marking configuration.
    """
    pass


@router.post("/sessions/{evaluation_id}/answers")
def register_answer_document(
    evaluation_id: UUID,
    payload: AnswerDocumentCreate
):
    """
    Register a student answer script.
    """
    pass


@router.post("/answers/{answer_id}/evaluate")
def evaluate_answer(answer_id: UUID):
    """
    Evaluate an answer document using rubric.
    """
    pass


@router.get("/answers/{answer_id}/result")
def get_evaluation_result(answer_id: UUID):
    """
    Get evaluation result for an answer.
    """
    pass
