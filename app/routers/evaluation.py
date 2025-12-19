from fastapi import APIRouter
from uuid import UUID
from app.schemas.evaluation import (
    EvaluationSessionCreate,
    EvaluationSessionUpdate,
    EvaluationSessionResponse,
    EvaluationResourceAttach,
    EvaluationResourceResponse,
    PaperConfigCreate,
    PaperConfigResponse,
    AnswerDocumentCreate,
    AnswerDocumentResponse,
    QuestionResponse,
    SubQuestionResponse,
    EvaluationResultDetail
)
from typing import List

router = APIRouter()


@router.post("/sessions", response_model=EvaluationSessionResponse)
def create_evaluation_session(payload: EvaluationSessionCreate):
    """
    Start a new evaluation session with a rubric.
    """
    pass


@router.get("/sessions", response_model=List[EvaluationSessionResponse])
def list_evaluation_sessions():
    """
    List all evaluation sessions.
    """
    pass


@router.get("/sessions/{evaluation_id}", response_model=EvaluationSessionResponse)
def get_evaluation_session(evaluation_id: UUID):
    """
    Get evaluation session details.
    """
    pass


@router.put("/sessions/{evaluation_id}", response_model=EvaluationSessionResponse)
def update_evaluation_session(evaluation_id: UUID, payload: EvaluationSessionUpdate):
    """
    Update evaluation session.
    """
    pass


@router.post("/sessions/{evaluation_id}/resources", response_model=EvaluationResourceResponse)
def attach_evaluation_resource(
    evaluation_id: UUID,
    payload: EvaluationResourceAttach
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


@router.get("/sessions/{evaluation_id}/questions", response_model=List[QuestionResponse])
def get_parsed_questions(evaluation_id: UUID):
    """
    Get parsed questions from question paper.
    """
    pass


@router.post("/sessions/{evaluation_id}/paper-config", response_model=PaperConfigResponse)
def save_paper_config(evaluation_id: UUID, payload: PaperConfigCreate):
    """
    Save paper marking configuration.
    """
    pass


@router.get("/sessions/{evaluation_id}/paper-config", response_model=PaperConfigResponse)
def get_paper_config(evaluation_id: UUID):
    """
    Get paper marking configuration.
    """
    pass


@router.post("/sessions/{evaluation_id}/answers", response_model=AnswerDocumentResponse)
def register_answer_document(
    evaluation_id: UUID,
    payload: AnswerDocumentCreate
):
    """
    Register a student answer script.
    """
    pass


@router.get("/sessions/{evaluation_id}/answers", response_model=List[AnswerDocumentResponse])
def list_answer_documents(evaluation_id: UUID):
    """
    List all answer documents for an evaluation session.
    """
    pass


@router.post("/answers/{answer_id}/evaluate")
def evaluate_answer(answer_id: UUID):
    """
    Evaluate an answer document using rubric.
    """
    pass


@router.get("/answers/{answer_id}/result", response_model=EvaluationResultDetail)
def get_evaluation_result(answer_id: UUID):
    """
    Get evaluation result for an answer.
    """
    pass
