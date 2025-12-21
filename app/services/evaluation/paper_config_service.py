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
        paper_part: Optional[str] = None,
        subject_name: Optional[str] = None,
        medium: Optional[str] = None,
        total_marks: Optional[int] = None,
        weightage: Optional[float] = None,
        total_main_questions: Optional[int] = None,
        selection_rules: Optional[dict] = None,
        is_confirmed: Optional[bool] = None,
    ):
        """Create or update paper config for a session."""
        existing_config = self.repository.get_paper_config(evaluation_session_id)

        if existing_config:
            return self.repository.update_paper_config(
                evaluation_session_id=evaluation_session_id,
                paper_part=paper_part,
                subject_name=subject_name,
                medium=medium,
                total_marks=total_marks,
                weightage=weightage,
                total_main_questions=total_main_questions,
                selection_rules=selection_rules,
                is_confirmed=is_confirmed,
            )

        # For create, no fields are strictly required anymore (all optional)
        return self.repository.create_paper_config(
            evaluation_session_id=evaluation_session_id,
            paper_part=paper_part,
            subject_name=subject_name,
            medium=medium,
            total_marks=total_marks,
            weightage=weightage,
            total_main_questions=total_main_questions,
            selection_rules=selection_rules,
            is_confirmed=is_confirmed or False,
        )

    def get_config(self, evaluation_session_id: UUID):
        """Fetch paper config for a session."""
        return self.repository.get_paper_config(evaluation_session_id)

    def confirm_config(
        self,
        evaluation_session_id: UUID,
        paper_part: Optional[str] = None,
        subject_name: Optional[str] = None,
        medium: Optional[str] = None,
        total_marks: Optional[int] = None,
        weightage: Optional[float] = None,
        total_main_questions: Optional[int] = None,
        selection_rules: Optional[dict] = None,
    ):
        """Update any provided fields and mark paper config as confirmed."""
        return self.repository.update_paper_config(
            evaluation_session_id=evaluation_session_id,
            paper_part=paper_part,
            subject_name=subject_name,
            medium=medium,
            total_marks=total_marks,
            weightage=weightage,
            total_main_questions=total_main_questions,
            selection_rules=selection_rules,
            is_confirmed=True,
        )