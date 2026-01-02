# app/services/chat_session_service.py

from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.chat_session_repository import ChatSessionRepository
from app.repositories.evaluation.evaluation_session_repository import EvaluationSessionRepository
from app.repositories.message_attachment_repository import MessageAttachmentRepository
from app.services.resource_service import ResourceService
from app.shared.models.message_relations import MessageAttachment
from app.shared.models.session_resources import SessionResource
from app.shared.models.evaluation_session import EvaluationResource
from app.shared.models.question_papers import QuestionPaper
from app.shared.models.answer_evaluation import AnswerDocument
import logging

logger = logging.getLogger(__name__)

class ChatSessionService:
    """Business logic for chat sessions."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = ChatSessionRepository(db)

    def create_session(
        self,
        user_id: UUID,
        mode: str,
        channel: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        grade: Optional[int] = None,
        subject: Optional[str] = None,
        rubric_id: Optional[UUID] = None,
    ):
        # Validation
        if not mode or not channel:
            raise ValueError("Mode and channel are required")
        
        final_rubric_id = rubric_id
        
        # Only apply global context logic for EVALUATION mode
        if mode == "evaluation":
            # 1. Get User Context (Global "Active" Settings)
            from app.services.evaluation.user_context_service import UserContextService
            context_service = UserContextService(self.db)
            context = context_service.get_or_create_context(user_id)
            
            # 2. Determine Rubric (Payload > Global Context)
            if not final_rubric_id:
                final_rubric_id = context.active_rubric_id
        
        # 3. Create Session
        session = self.repository.create_session(
            user_id=user_id,
            mode=mode,
            channel=channel,
            title=title,
            description=description,
            grade=grade,
            subject=subject,
            rubric_id=final_rubric_id,
        )
        
        # 4. Copy Active Resources (Syllabus, Question Paper) to this Session (Only for Evaluation)
        if mode == "evaluation":
            if context.active_syllabus_id:
                self.repository.attach_resource(session.id, context.active_syllabus_id, "syllabus")
                
            if context.active_question_paper_id:
                self.repository.attach_resource(session.id, context.active_question_paper_id, "question_paper")
            
        return session

    def get_session(self, session_id: UUID):
        return self.repository.get_session(session_id)

    def list_user_sessions(self, user_id: UUID) -> List:
        return self.repository.list_user_sessions(user_id)

    def validate_ownership(self, session_id: UUID, user_id: UUID) -> bool:
        return self.repository.validate_ownership(session_id, user_id)
    
    def get_session_with_ownership_check(self, session_id: UUID, user_id: UUID):
        """Get session and verify ownership. Raises exceptions if invalid."""
        if not self.validate_ownership(session_id, user_id):
            raise PermissionError("You don't have permission to access this session")
        
        session = self.get_session(session_id)
        if not session:
            raise ValueError("Chat session not found")
        
        return session
    
    def update_session(
        self,
        session_id: UUID,
        user_id: UUID,
        title: Optional[str] = None,
        description: Optional[str] = None,
        grade: Optional[int] = None,
        subject: Optional[str] = None,
        rubric_id: Optional[UUID] = None,
    ):
        """Update session after ownership validation."""
        session = self.get_session_with_ownership_check(session_id, user_id)
        
        # Update fields if provided
        if title is not None:
            session.title = title
        if description is not None:
            session.description = description
        if grade is not None:
            session.grade = grade
        if subject is not None:
            session.subject = subject
        if rubric_id is not None:
            session.rubric_id = rubric_id
            # Update Global Context if in Evaluation Mode
            if session.mode == "evaluation":
                from app.services.evaluation.user_context_service import UserContextService
                context_service = UserContextService(self.db)
                context_service.update_rubric(user_id, rubric_id)
        
        self.db.commit()
        self.db.refresh(session)
        return session
    
    def delete_session(self, session_id: UUID, user_id: UUID):
        """Delete session after ownership validation."""
        session = self.get_session_with_ownership_check(session_id, user_id)

        try:
            if session.mode == "evaluation":
                eval_repo = EvaluationSessionRepository(self.db)

                # Delete dependent evaluation data first (no DB-level cascade defined)
                eval_ids = eval_repo.get_evaluation_session_ids_by_chat_session(session_id)

                if eval_ids:
                    eval_repo.delete_resources_by_evaluation_ids(eval_ids)
                    eval_repo.delete_paper_configs_by_evaluation_ids(eval_ids)
                    eval_repo.delete_evaluation_sessions_by_ids(eval_ids)
            else:
                # Learning mode: remove attachments and orphaned resources
                att_repo = MessageAttachmentRepository(self.db)
                candidate_resource_ids = att_repo.get_resource_ids_for_session(session_id)

                # First, delete attachments
                att_repo.delete_attachments_by_session_id(session_id)

                # Then, delete any orphaned resources no longer referenced anywhere
                if candidate_resource_ids:
                    resource_service = ResourceService(self.db)
                    for rid in set(candidate_resource_ids):
                        # Check remaining references across link tables
                        remaining_refs = 0
                        remaining_refs += self.db.query(MessageAttachment).filter(MessageAttachment.resource_id == rid).count()
                        remaining_refs += self.db.query(SessionResource).filter(SessionResource.resource_id == rid).count()
                        remaining_refs += self.db.query(EvaluationResource).filter(EvaluationResource.resource_id == rid).count()
                        remaining_refs += self.db.query(QuestionPaper).filter(QuestionPaper.resource_id == rid).count()
                        remaining_refs += self.db.query(AnswerDocument).filter(AnswerDocument.resource_id == rid).count()

                        if remaining_refs == 0:
                            try:
                                resource_service.delete_resource(rid, session.user_id, commit=False)
                            except Exception:
                                # If deletion fails for one resource, continue; final commit/rollback will handle transaction
                                logger.warning("Failed to delete resource %s during session cleanup", rid)

            # Always delete the chat session itself
            self.db.delete(session)
            self.db.commit()

        except Exception:
            self.db.rollback()
            raise
    
    def attach_resource(self, session_id: UUID, user_id: UUID, resource_id: UUID, role: str):
        """Attach a resource to session with a specific role."""
        # Verify ownership
        session = self.get_session_with_ownership_check(session_id, user_id)
        
        # Verify resource ownership (optional but good practice)
        from app.services.resource_service import ResourceService
        resource_service = ResourceService(self.db)
        resource_service.get_resource_with_ownership_check(resource_id, user_id)
        
        # 1. Attach to this specific session
        self.repository.attach_resource(session_id, resource_id, role)
        
        # 2. Update Global Context (so future chats use this new resource by default)
        # Only if this is an EVALUATION session
        if session.mode == "evaluation":
            from app.services.evaluation.user_context_service import UserContextService
            context_service = UserContextService(self.db)
            
            if role == "syllabus":
                context_service.update_syllabus(user_id, resource_id)
            elif role == "question_paper":
                context_service.update_question_paper(user_id, resource_id)
            
        return {"detail": f"Resource attached as {role} successfully"}

