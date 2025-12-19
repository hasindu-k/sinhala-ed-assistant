# app/services/evaluation/evaluation_session_service.py

from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.shared.models.evaluation_session import EvaluationSession, EvaluationResource, PaperConfig


def create_evaluation_session(
    *,
    db: Session,
    session_id: UUID,
    rubric_id: Optional[UUID] = None,
    status: str = "pending"
) -> EvaluationSession:
    """Create a new evaluation session."""
    eval_session = EvaluationSession(
        session_id=session_id,
        rubric_id=rubric_id,
        status=status
    )
    db.add(eval_session)
    db.commit()
    db.refresh(eval_session)
    return eval_session


def get_evaluation_session(
    *,
    db: Session,
    evaluation_session_id: UUID
) -> Optional[EvaluationSession]:
    """Get evaluation session by ID."""
    return db.query(EvaluationSession).filter(
        EvaluationSession.id == evaluation_session_id
    ).first()


def get_evaluation_sessions_by_chat_session(
    *,
    db: Session,
    session_id: UUID
) -> List[EvaluationSession]:
    """Get all evaluation sessions for a chat session."""
    return db.query(EvaluationSession).filter(
        EvaluationSession.session_id == session_id
    ).all()


def update_evaluation_status(
    *,
    db: Session,
    evaluation_session_id: UUID,
    status: str
) -> Optional[EvaluationSession]:
    """Update evaluation session status."""
    eval_session = get_evaluation_session(db=db, evaluation_session_id=evaluation_session_id)
    if eval_session:
        eval_session.status = status
        db.commit()
        db.refresh(eval_session)
    return eval_session


def add_evaluation_resource(
    *,
    db: Session,
    evaluation_session_id: UUID,
    resource_id: UUID,
    role: str
) -> EvaluationResource:
    """Link a resource to an evaluation session with a specific role."""
    eval_resource = EvaluationResource(
        evaluation_session_id=evaluation_session_id,
        resource_id=resource_id,
        role=role  # 'syllabus', 'question_paper', 'answer_script'
    )
    db.add(eval_resource)
    db.commit()
    db.refresh(eval_resource)
    return eval_resource


def get_evaluation_resources(
    *,
    db: Session,
    evaluation_session_id: UUID,
    role: Optional[str] = None
) -> List[EvaluationResource]:
    """Get resources linked to an evaluation session, optionally filtered by role."""
    query = db.query(EvaluationResource).filter(
        EvaluationResource.evaluation_session_id == evaluation_session_id
    )
    if role:
        query = query.filter(EvaluationResource.role == role)
    return query.all()


def create_paper_config(
    *,
    db: Session,
    evaluation_session_id: UUID,
    total_marks: int,
    total_main_questions: int,
    required_questions: int
) -> PaperConfig:
    """Create paper configuration for an evaluation session."""
    paper_config = PaperConfig(
        evaluation_session_id=evaluation_session_id,
        total_marks=total_marks,
        total_main_questions=total_main_questions,
        required_questions=required_questions
    )
    db.add(paper_config)
    db.commit()
    db.refresh(paper_config)
    return paper_config


def get_paper_config(
    *,
    db: Session,
    evaluation_session_id: UUID
) -> Optional[PaperConfig]:
    """Get paper configuration for an evaluation session."""
    return db.query(PaperConfig).filter(
        PaperConfig.evaluation_session_id == evaluation_session_id
    ).first()


def update_paper_config(
    *,
    db: Session,
    evaluation_session_id: UUID,
    total_marks: Optional[int] = None,
    total_main_questions: Optional[int] = None,
    required_questions: Optional[int] = None
) -> Optional[PaperConfig]:
    """Update paper configuration."""
    config = get_paper_config(db=db, evaluation_session_id=evaluation_session_id)
    if config:
        if total_marks is not None:
            config.total_marks = total_marks
        if total_main_questions is not None:
            config.total_main_questions = total_main_questions
        if required_questions is not None:
            config.required_questions = required_questions
        db.commit()
        db.refresh(config)
    return config