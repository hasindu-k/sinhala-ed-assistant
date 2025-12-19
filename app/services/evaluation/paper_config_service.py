from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.evaluation.evaluation_session_repository import EvaluationSessionRepository


class PaperConfigService:
    """Business logic for paper configuration tied to evaluation sessions."""

    def __init__(self, db: Session):
        self.repository = EvaluationSessionRepository(db)

    def save_config(
        self,
        evaluation_session_id: UUID,
        total_marks: Optional[int] = None,
        total_main_questions: Optional[int] = None,
        required_questions: Optional[int] = None,
    ):
        """Create or update paper config for a session."""
        existing_config = self.repository.get_paper_config(evaluation_session_id)

        if existing_config:
            return self.repository.update_paper_config(
                evaluation_session_id=evaluation_session_id,
                total_marks=total_marks,
                total_main_questions=total_main_questions,
                required_questions=required_questions,
            )

        if total_marks is None or total_main_questions is None or required_questions is None:
            raise ValueError(
                "total_marks, total_main_questions, and required_questions are required to create a paper config."
            )

        return self.repository.create_paper_config(
            evaluation_session_id=evaluation_session_id,
            total_marks=total_marks,
            total_main_questions=total_main_questions,
            required_questions=required_questions,
        )

    def get_config(self, evaluation_session_id: UUID):
        """Fetch paper config for a session."""
        return self.repository.get_paper_config(evaluation_session_id)