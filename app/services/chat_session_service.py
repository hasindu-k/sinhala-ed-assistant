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
    ):
        # Validation
        if not mode or not channel:
            raise ValueError("Mode and channel are required")
        
        return self.repository.create_session(
            user_id=user_id,
            mode=mode,
            channel=channel,
            title=title,
            description=description,
            grade=grade,
            subject=subject,
        )

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
        
        self.db.commit()
        self.db.refresh(session)
        return session
    
    def delete_session(self, session_id: UUID, user_id: UUID):
        """Delete session after ownership validation."""
        session = self.get_session_with_ownership_check(session_id, user_id)
        
        self.db.delete(session)
        self.db.commit()
    
    def attach_resources(self, session_id: UUID, user_id: UUID, resource_ids: List[UUID]):
        """Attach resources to session after validation."""
        if not resource_ids:
            raise ValueError("At least one resource ID is required")
        
        # Verify ownership
        self.get_session_with_ownership_check(session_id, user_id)
        
        # TODO: Implement actual resource attachment logic
        # This would involve creating records in session_resources table
        return {"detail": "Resources attached successfully"}
