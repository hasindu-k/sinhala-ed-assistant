# app/services/evaluation/evaluation_session_service.py

from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.evaluation.evaluation_session_repository import EvaluationSessionRepository


class EvaluationSessionService:
    """Business logic for evaluation session management."""
    
    def __init__(self, db: Session):
        self.repository = EvaluationSessionRepository(db)
    
    def create_evaluation_session(
        self,
        session_id: UUID,
        rubric_id: Optional[UUID] = None,
        status: str = "pending"
    ):
        """Create a new evaluation session."""
        return self.repository.create_evaluation_session(
            session_id=session_id,
            rubric_id=rubric_id,
            status=status
        )
    
    def get_evaluation_session(self, evaluation_session_id: UUID):
        """Get evaluation session by ID."""
        return self.repository.get_evaluation_session(evaluation_session_id)
    
    def get_evaluation_sessions_by_chat_session(self, session_id: UUID) -> List:
        """Get all evaluation sessions for a chat session."""
        return self.repository.get_evaluation_sessions_by_chat_session(session_id)

    def list_all_sessions(self) -> List:
        """Get every evaluation session."""
        return self.repository.list_all_sessions()
    
    def update_evaluation_status(
        self,
        evaluation_session_id: UUID,
        status: str
    ):
        """Update evaluation session status."""
        return self.repository.update_evaluation_status(
            evaluation_session_id=evaluation_session_id,
            status=status
        )

    def update_evaluation_session(
        self,
        evaluation_session_id: UUID,
        status: Optional[str] = None,
        rubric_id: Optional[UUID] = None
    ):
        """Update evaluation session metadata."""
        return self.repository.update_evaluation_session(
            evaluation_session_id=evaluation_session_id,
            status=status,
            rubric_id=rubric_id,
        )
    
    def add_evaluation_resource(
        self,
        evaluation_session_id: UUID,
        resource_id: UUID,
        role: str
    ):
        """Link a resource to an evaluation session with a specific role."""
        return self.repository.add_evaluation_resource(
            evaluation_session_id=evaluation_session_id,
            resource_id=resource_id,
            role=role
        )
    
    def get_evaluation_resources(
        self,
        evaluation_session_id: UUID,
        role: Optional[str] = None
    ) -> List:
        """Get resources linked to an evaluation session, optionally filtered by role."""
        return self.repository.get_evaluation_resources(
            evaluation_session_id=evaluation_session_id,
            role=role
        )
    
    def create_paper_config(
        self,
        evaluation_session_id: UUID,
        paper_part: Optional[str] = None,
        subject_name: Optional[str] = None,
        medium: Optional[str] = None,
        weightage: Optional[float] = None,
        total_main_questions: Optional[int] = None,
        selection_rules: Optional[dict] = None,
        is_confirmed: Optional[bool] = False,
    ):
        """Create paper configuration for an evaluation session."""
        return self.repository.create_paper_config(
            evaluation_session_id=evaluation_session_id,
            paper_part=paper_part,
            subject_name=subject_name,
            medium=medium,
            weightage=weightage,
            total_main_questions=total_main_questions,
            selection_rules=selection_rules,
            is_confirmed=is_confirmed,
        )
    
    def get_paper_config(self, evaluation_session_id: UUID, paper_part: Optional[str] = None):
        """Get paper configuration for an evaluation session."""
        return self.repository.get_paper_config(evaluation_session_id, paper_part)
    
    def update_paper_config(
        self,
        evaluation_session_id: UUID,
        paper_part: Optional[str] = None,
        subject_name: Optional[str] = None,
        medium: Optional[str] = None,
        weightage: Optional[float] = None,
        total_main_questions: Optional[int] = None,
        selection_rules: Optional[dict] = None,
        is_confirmed: Optional[bool] = None,
    ):
        """Update paper configuration."""
        return self.repository.update_paper_config(
            evaluation_session_id=evaluation_session_id,
            paper_part=paper_part,
            subject_name=subject_name,
            medium=medium,
            weightage=weightage,
            total_main_questions=total_main_questions,
            selection_rules=selection_rules,
            is_confirmed=is_confirmed,
        )
