# app/services/chat_session_service.py

from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.chat_session_repository import ChatSessionRepository


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
        
        self.db.commit()
        self.db.refresh(session)
        return session
    
    def delete_session(self, session_id: UUID, user_id: UUID):
        """Delete session after ownership validation."""
        session = self.get_session_with_ownership_check(session_id, user_id)
        
        self.db.delete(session)
        self.db.commit()
    
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

