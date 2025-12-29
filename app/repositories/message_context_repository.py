# app/repositories/message_context_repository.py

from typing import List, Optional, Dict
from uuid import UUID
from sqlalchemy.orm import Session

from app.shared.models.message_relations import MessageContextChunk


class MessageContextRepository:
    """Data access for MessageContextChunk."""

    def __init__(self, db: Session):
        self.db = db

    def log_used_chunks(self, message_id: UUID, chunks: List[Dict]) -> List[MessageContextChunk]:
        """
        chunks: List[{
            "chunk_id": UUID,
            "similarity_score": Optional[float],
            "rank": Optional[int],
        }]
        """
        created: List[MessageContextChunk] = []
        for c in chunks:
            row = MessageContextChunk(
                message_id=message_id,
                chunk_id=c["chunk_id"],
                similarity_score=c.get("similarity_score"),
                rank=c.get("rank"),
            )
            self.db.add(row)
            created.append(row)
        self.db.commit()
        for row in created:
            self.db.refresh(row)
        return created

    def get_message_sources(self, message_id: UUID) -> List[MessageContextChunk]:
        return (
            self.db.query(MessageContextChunk)
            .filter(MessageContextChunk.message_id == message_id)
            .order_by(MessageContextChunk.rank.asc().nulls_last())
            .all()
        )
