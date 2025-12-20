import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

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
    EvaluationResultDetail,
)
from app.services.evaluation.evaluation_workflow_service import EvaluationWorkflowService
from app.core.database import get_db
from app.core.security import get_current_user
from app.shared.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/sessions", response_model=EvaluationSessionResponse)
def create_evaluation_session(
    payload: EvaluationSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Start a new evaluation session with a rubric.
    """
    service = EvaluationWorkflowService(db)
    try:
        return service.create_session(payload, current_user.id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.error(f"Failed to create evaluation session for chat {payload.session_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create evaluation session")


@router.get("/sessions", response_model=List[EvaluationSessionResponse])
def list_evaluation_sessions(
    session_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all evaluation sessions for the current user (or a specific chat session).
    """
    service = EvaluationWorkflowService(db)
    try:
        return service.list_sessions(current_user.id, session_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except Exception as exc:
        logger.error(f"Failed to list evaluation sessions: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list evaluation sessions")


@router.get("/sessions/{evaluation_id}", response_model=EvaluationSessionResponse)
def get_evaluation_session(
    evaluation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get evaluation session details.
    """
    service = EvaluationWorkflowService(db)
    try:
        return service.get_session(evaluation_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.put("/sessions/{evaluation_id}", response_model=EvaluationSessionResponse)
def update_evaluation_session(
    evaluation_id: UUID,
    payload: EvaluationSessionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update evaluation session.
    """
    service = EvaluationWorkflowService(db)
    try:
        updated = service.update_session(evaluation_id, payload, current_user.id)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation session not found")
        return updated
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.post("/sessions/{evaluation_id}/resources", response_model=EvaluationResourceResponse)
def attach_evaluation_resource(
    evaluation_id: UUID,
    payload: EvaluationResourceAttach,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Attach syllabus / question paper / answer script.
    """
    service = EvaluationWorkflowService(db)
    try:
        return service.attach_resource(evaluation_id, payload, current_user.id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.error(f"Failed to attach resource to evaluation {evaluation_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to attach evaluation resource")


@router.post("/sessions/{evaluation_id}/parse-paper")
def parse_question_paper(
    evaluation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Extract question structure from question paper.
    """
    service = EvaluationWorkflowService(db)
    try:
        return service.parse_question_paper(evaluation_id, current_user.id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error(f"Failed to parse question paper for evaluation {evaluation_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to parse question paper")


@router.get("/sessions/{evaluation_id}/questions", response_model=List[QuestionResponse])
def get_parsed_questions(
    evaluation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get parsed questions from question paper.
    """
    service = EvaluationWorkflowService(db)
    try:
        return service.get_parsed_questions(evaluation_id, current_user.id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except Exception as exc:
        logger.error(f"Failed to fetch parsed questions for evaluation {evaluation_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch parsed questions")


@router.post("/sessions/{evaluation_id}/paper-config", response_model=PaperConfigResponse)
def save_paper_config(
    evaluation_id: UUID,
    payload: PaperConfigCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Save paper marking configuration.
    """
    service = EvaluationWorkflowService(db)
    try:
        return service.save_paper_config(evaluation_id, payload, current_user.id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error(f"Failed to save paper config for evaluation {evaluation_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save paper config")


@router.get("/sessions/{evaluation_id}/paper-config", response_model=PaperConfigResponse)
def get_paper_config(
    evaluation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get paper marking configuration.
    """
    service = EvaluationWorkflowService(db)
    try:
        config = service.get_paper_config(evaluation_id, current_user.id)
        if not config:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper config not found")
        return config
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/sessions/{evaluation_id}/answers", response_model=AnswerDocumentResponse)
def register_answer_document(
    evaluation_id: UUID,
    payload: AnswerDocumentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Register a student answer script.
    """
    service = EvaluationWorkflowService(db)
    try:
        return service.register_answer_document(evaluation_id, payload, current_user.id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.error(f"Failed to register answer for evaluation {evaluation_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to register answer document")


@router.get("/sessions/{evaluation_id}/answers", response_model=List[AnswerDocumentResponse])
def list_answer_documents(
    evaluation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all answer documents for an evaluation session.
    """
    service = EvaluationWorkflowService(db)
    try:
        return service.list_answer_documents(evaluation_id, current_user.id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except Exception as exc:
        logger.error(f"Failed to list answers for evaluation {evaluation_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list answer documents")


@router.post("/answers/{answer_id}/evaluate")
def evaluate_answer(
    answer_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Evaluate an answer document using rubric.
    """
    service = EvaluationWorkflowService(db)
    try:
        result = service.evaluate_answer(answer_id, current_user.id)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found for evaluation")
        return {"evaluation_result_id": result.id}
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to evaluate answer {answer_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to evaluate answer")


@router.get("/answers/{answer_id}/result", response_model=EvaluationResultDetail)
def get_evaluation_result(
    answer_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get evaluation result for an answer.
    """
    service = EvaluationWorkflowService(db)
    try:
        result = service.get_evaluation_result(answer_id, current_user.id)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation result not found")
        return result
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
