# app/services/message_context_service.py

from typing import List, Dict
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.message_context_repository import MessageContextRepository


class MessageContextService:
    """Business logic for message context (used chunks)."""

    def __init__(self, db: Session):
        self.repository = MessageContextRepository(db)

    def log_used_chunks(self, message_id: UUID, chunks: List[Dict]):
        return self.repository.log_used_chunks(message_id, chunks)

    def get_message_sources(self, message_id: UUID):
        return self.repository.get_message_sources(message_id)