from typing import List, Dict
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.resource_chunk_repository import ResourceChunkRepository


class ResourceChunkService:
    """Business logic for resource chunks and search."""

    def __init__(self, db: Session):
        self.repository = ResourceChunkRepository(db)

    def create_chunks(self, resource_id: UUID, chunks: List[Dict]):
        """Persist precomputed chunks (content + optional embeddings)."""
        return self.repository.create_chunks(resource_id, chunks)

    def get_chunks_by_resource(self, resource_ids: List[UUID]):
        return self.repository.get_chunks_by_resource(resource_ids)

    def vector_search(self, resource_ids: List[UUID], query_embedding: List[float], top_k: int = 10):
        return self.repository.vector_search(resource_ids, query_embedding, top_k)
