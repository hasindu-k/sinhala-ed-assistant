# app/repositories/evaluation/evaluation_session_repository.py

from typing import Optional, List, Union
from uuid import UUID
from sqlalchemy.orm import Session

from app.shared.models.evaluation_session import EvaluationSession, EvaluationResource, PaperConfig


class EvaluationSessionRepository:
    """Data access layer for evaluation session models."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_evaluation_session(
        self,
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
        self.db.add(eval_session)
        self.db.commit()
        self.db.refresh(eval_session)
        return eval_session
    
    def get_evaluation_session(self, evaluation_session_id: UUID) -> Optional[EvaluationSession]:
        """Get evaluation session by ID."""
        return self.db.query(EvaluationSession).filter(
            EvaluationSession.id == evaluation_session_id
        ).first()
    
    def get_evaluation_sessions_by_chat_session(self, session_id: UUID) -> List[EvaluationSession]:
        """Get all evaluation sessions for a chat session."""
        return self.db.query(EvaluationSession).filter(
            EvaluationSession.session_id == session_id
        ).all()

    def get_evaluation_session_ids_by_chat_session(self, session_id: UUID) -> List[UUID]:
        """Get only IDs of evaluation sessions for a chat session."""
        return (
            self.db.query(EvaluationSession.id)
            .filter(EvaluationSession.session_id == session_id)
            .scalars()
            .all()
        )

    def list_all_sessions(self) -> List[EvaluationSession]:
        """Get all evaluation sessions."""
        return self.db.query(EvaluationSession).all()
    
    def update_evaluation_status(
        self,
        evaluation_session_id: UUID,
        status: str
    ) -> Optional[EvaluationSession]:
        """Update evaluation session status."""
        eval_session = self.get_evaluation_session(evaluation_session_id)
        if eval_session:
            eval_session.status = status
            self.db.commit()
            self.db.refresh(eval_session)
        return eval_session

    def update_evaluation_session(
        self,
        evaluation_session_id: UUID,
        status: Optional[str] = None,
        rubric_id: Optional[UUID] = None
    ) -> Optional[EvaluationSession]:
        """Update evaluation session metadata."""
        eval_session = self.get_evaluation_session(evaluation_session_id)
        if not eval_session:
            return None

        if status is not None:
            eval_session.status = status
        if rubric_id is not None:
            eval_session.rubric_id = rubric_id

        self.db.commit()
        self.db.refresh(eval_session)
        return eval_session
    
    def add_evaluation_resource(
        self,
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
        self.db.add(eval_resource)
        self.db.commit()
        self.db.refresh(eval_resource)
        return eval_resource
    
    def get_evaluation_resources(
        self,
        evaluation_session_id: UUID,
        role: Optional[str] = None
    ) -> List[EvaluationResource]:
        """Get resources linked to an evaluation session, optionally filtered by role."""
        query = self.db.query(EvaluationResource).filter(
            EvaluationResource.evaluation_session_id == evaluation_session_id
        )
        if role:
            query = query.filter(EvaluationResource.role == role)
        return query.all()

    def delete_resources_by_evaluation_ids(self, evaluation_ids: List[UUID], *, commit: bool = False) -> int:
        """Bulk delete EvaluationResource rows for given evaluation session IDs."""
        if not evaluation_ids:
            return 0
        count = (
            self.db.query(EvaluationResource)
            .filter(EvaluationResource.evaluation_session_id.in_(evaluation_ids))
            .delete(synchronize_session=False)
        )
        if commit:
            self.db.commit()
        return count

    def delete_paper_configs_by_evaluation_ids(self, evaluation_ids: List[UUID], *, commit: bool = False) -> int:
        """Bulk delete PaperConfig rows for given evaluation session IDs."""
        if not evaluation_ids:
            return 0
        count = (
            self.db.query(PaperConfig)
            .filter(PaperConfig.evaluation_session_id.in_(evaluation_ids))
            .delete(synchronize_session=False)
        )
        if commit:
            self.db.commit()
        return count

    def delete_evaluation_sessions_by_ids(self, evaluation_ids: List[UUID], *, commit: bool = False) -> int:
        """Bulk delete EvaluationSession rows by IDs."""
        if not evaluation_ids:
            return 0
        count = (
            self.db.query(EvaluationSession)
            .filter(EvaluationSession.id.in_(evaluation_ids))
            .delete(synchronize_session=False)
        )
        if commit:
            self.db.commit()
        return count
    
    def create_paper_config(
        self,
        chat_session_id: Optional[UUID] = None,
        evaluation_session_id: Optional[UUID] = None,
        paper_part: Optional[str] = None,
        subject_name: Optional[str] = None,
        medium: Optional[str] = None,
        total_marks: Optional[int] = None,
        weightage: Optional[float] = None,
        total_main_questions: Optional[int] = None,
        selection_rules: Optional[dict] = None,
        is_confirmed: Optional[bool] = False,
    ) -> PaperConfig:
        """Create paper configuration for an evaluation session or chat session."""
        paper_config = PaperConfig(
            chat_session_id=chat_session_id,
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
        self.db.add(paper_config)
        self.db.commit()
        self.db.refresh(paper_config)
        return paper_config
    
    def get_paper_config(
        self,
        evaluation_session_id: Optional[UUID] = None,
        chat_session_id: Optional[UUID] = None,
        paper_part: Optional[str] = None,
    ) -> Union[Optional[PaperConfig], List[PaperConfig]]:
        """Get paper configuration for an evaluation session or chat session (optionally by paper)."""
        query = self.db.query(PaperConfig)
        
        if evaluation_session_id:
            query = query.filter(PaperConfig.evaluation_session_id == evaluation_session_id)
        elif chat_session_id:
            query = query.filter(PaperConfig.chat_session_id == chat_session_id)
        else:
            return None
            
        if paper_part is not None:
            query = query.filter(PaperConfig.paper_part == paper_part)
            return query.first()
        
        return query.all()
    
    def _apply_paper_config_updates(
        self,
        config: PaperConfig,
        paper_part: Optional[str] = None,
        subject_name: Optional[str] = None,
        medium: Optional[str] = None,
        total_marks: Optional[int] = None,
        weightage: Optional[float] = None,
        total_main_questions: Optional[int] = None,
        selection_rules: Optional[dict] = None,
        is_confirmed: Optional[bool] = None,
    ) -> None:
        """Apply updates to paper configuration object."""
        if paper_part is not None:
            config.paper_part = paper_part
        if subject_name is not None:
            config.subject_name = subject_name
        if medium is not None:
            config.medium = medium
        if total_marks is not None:
            config.total_marks = total_marks
        if weightage is not None:
            config.weightage = weightage
        if total_main_questions is not None:
            config.total_main_questions = total_main_questions
        if selection_rules is not None:
            config.selection_rules = selection_rules
        if is_confirmed is not None:
            config.is_confirmed = is_confirmed

    def update_paper_config(
        self,
        evaluation_session_id: Optional[UUID] = None,
        chat_session_id: Optional[UUID] = None,
        paper_part: Optional[str] = None,
        subject_name: Optional[str] = None,
        medium: Optional[str] = None,
        total_marks: Optional[int] = None,
        weightage: Optional[float] = None,
        total_main_questions: Optional[int] = None,
        selection_rules: Optional[dict] = None,
        is_confirmed: Optional[bool] = None,
    ) -> Union[PaperConfig, List[PaperConfig], None]:
        """Update paper configuration."""
        configs = self.get_paper_config(evaluation_session_id, chat_session_id, paper_part)
        
        if not configs:
            return None
            
        # Normalize to list for processing
        if isinstance(configs, list):
            configs_list = configs
        else:
            configs_list = [configs]

        for config in configs_list:
            self._apply_paper_config_updates(
                config,
                paper_part=paper_part if paper_part else None,
                subject_name=subject_name,
                medium=medium,
                total_marks=total_marks,
                weightage=weightage,
                total_main_questions=total_main_questions,
                selection_rules=selection_rules,
                is_confirmed=is_confirmed,
            )
            
        self.db.commit()
        for config in configs_list:
            self.db.refresh(config)
            
        return configs
