from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.services.chat_session_repository import ChatSessionRepository


class ChatSessionService:
    """Business logic for chat sessions."""

    def __init__(self, db: Session):
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
