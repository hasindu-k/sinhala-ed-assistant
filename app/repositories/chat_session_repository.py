# app/repositories/chat_session_repository.py

from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.shared.models.chat_session import ChatSession
from app.shared.models.session_resources import SessionResource


class ChatSessionRepository:
    """Data access layer for ChatSession."""

    def __init__(self, db: Session):
        self.db = db

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
    ) -> ChatSession:
        session = ChatSession(
            user_id=user_id,
            mode=mode,
            channel=channel,
            title=title,
            description=description,
            grade=grade,
            subject=subject,
            rubric_id=rubric_id,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session(self, session_id: UUID) -> Optional[ChatSession]:
        return self.db.query(ChatSession).filter(ChatSession.id == session_id).first()

    def list_user_sessions(self, user_id: UUID) -> List[ChatSession]:
        return (
            self.db.query(ChatSession)
            .filter(ChatSession.user_id == user_id)
            .order_by(ChatSession.created_at.desc())
            .all()
        )

    def validate_ownership(self, session_id: UUID, user_id: UUID) -> bool:
        session = (
            self.db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .first()
        )
        return session is not None

    def attach_resource(self, session_id: UUID, resource_id: UUID, role: str):
        """Attach a resource to a session with a specific role (label)."""
        # Check if resource is already attached
        existing = self.db.query(SessionResource).filter(
            SessionResource.session_id == session_id,
            SessionResource.resource_id == resource_id
        ).first()
        
        if existing:
            existing.label = role
        else:
            # Check if a resource with this role already exists for this session, if so, replace it?
            # The user said "latest uploaded things until user upload new ones".
            # So if we attach a new "question_paper", we should probably remove the old "question_paper".
            if role in ["question_paper", "syllabus"]:
                self.db.query(SessionResource).filter(
                    SessionResource.session_id == session_id,
                    SessionResource.label == role
                ).delete()
            
            session_resource = SessionResource(
                session_id=session_id,
                resource_id=resource_id,
                label=role
            )
            self.db.add(session_resource)
        
        self.db.commit()

