# app/services/chat_session_repository.py

from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.shared.models.chat_session import ChatSession


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
    ) -> ChatSession:
        session = ChatSession(
            user_id=user_id,
            mode=mode,
            channel=channel,
            title=title,
            description=description,
            grade=grade,
            subject=subject,
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
