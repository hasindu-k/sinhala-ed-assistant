from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.evaluation.evaluation_session_repository import EvaluationSessionRepository


class EvaluationResourceService:
    """Business logic for linking resources to evaluation sessions."""

    def __init__(self, db: Session):
        self.repository = EvaluationSessionRepository(db)

    def attach_resource(self, evaluation_session_id: UUID, resource_id: UUID, role: str):
        """Attach a resource (syllabus, question paper, answer script) to a session."""
        return self.repository.add_evaluation_resource(
            evaluation_session_id=evaluation_session_id,
            resource_id=resource_id,
            role=role,
        )

    def get_resources_by_role(
        self,
        evaluation_session_id: UUID,
        role: Optional[str] = None,
    ) -> List:
        """Fetch resources for a session, optionally filtered by role."""
        return self.repository.get_evaluation_resources(
            evaluation_session_id=evaluation_session_id,
            role=role,
        )