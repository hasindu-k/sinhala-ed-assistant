from typing import Optional, List, Dict
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.message_repository import MessageRepository


class MessageService:
    """Business logic for chat messages."""

    def __init__(self, db: Session):
        self.repository = MessageRepository(db)

    def create_user_message(
        self,
        session_id: UUID,
        content: Optional[str],
        modality: str = "text",
        grade_level: Optional[str] = None,
        audio_url: Optional[str] = None,
        transcript: Optional[str] = None,
        audio_duration_sec: Optional[float] = None,
    ):
        return self.repository.create_user_message(
            session_id=session_id,
            content=content,
            modality=modality,
            grade_level=grade_level,
            audio_url=audio_url,
            transcript=transcript,
            audio_duration_sec=audio_duration_sec,
        )

    def create_system_message(self, session_id: UUID, content: Optional[str]):
        return self.repository.create_system_message(session_id, content)

    def create_assistant_message(
        self,
        session_id: UUID,
        content: Optional[str],
        model_info: Optional[Dict] = None,
    ):
        return self.repository.create_assistant_message(
            session_id=session_id,
            content=content,
            model_info=model_info,
        )

    def list_session_messages(self, session_id: UUID) -> List:
        return self.repository.list_session_messages(session_id)
