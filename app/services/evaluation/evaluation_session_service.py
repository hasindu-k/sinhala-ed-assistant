# app/services/evaluation/evaluation_session_service.py

from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.services.evaluation.evaluation_session_repository import EvaluationSessionRepository


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
        total_marks: int,
        total_main_questions: int,
        required_questions: int
    ):
        """Create paper configuration for an evaluation session."""
        return self.repository.create_paper_config(
            evaluation_session_id=evaluation_session_id,
            total_marks=total_marks,
            total_main_questions=total_main_questions,
            required_questions=required_questions
        )
    
    def get_paper_config(self, evaluation_session_id: UUID):
        """Get paper configuration for an evaluation session."""
        return self.repository.get_paper_config(evaluation_session_id)
    
    def update_paper_config(
        self,
        evaluation_session_id: UUID,
        total_marks: Optional[int] = None,
        total_main_questions: Optional[int] = None,
        required_questions: Optional[int] = None
    ):
        """Update paper configuration."""
        return self.repository.update_paper_config(
            evaluation_session_id=evaluation_session_id,
            total_marks=total_marks,
            total_main_questions=total_main_questions,
            required_questions=required_questions
        )
