# app/repositories/resource_chunk_repository.py

from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.shared.models.resource_chunks import ResourceChunk


class ResourceChunkRepository:
    """Data access for ResourceChunk and vector search."""

    def __init__(self, db: Session):
        self.db = db

    def create_chunks(self, resource_id: UUID, chunks: List[dict]) -> List[ResourceChunk]:
        """
        Persist a list of chunk dicts:
        {
          "content": str,
          "chunk_index": Optional[int],
          "embedding": Optional[List[float]],
          "embedding_model": Optional[str],
          "token_count": Optional[int],
          "content_length": Optional[int],
          "start_char": Optional[int],
          "end_char": Optional[int]
        }
        """
        rows: List[ResourceChunk] = []
        for c in chunks:
            row = ResourceChunk(
                resource_id=resource_id,
                content=c.get("content"),
                chunk_index=c.get("chunk_index"),
                embedding=c.get("embedding"),
                embedding_model=c.get("embedding_model"),
                token_count=c.get("token_count"),
                content_length=c.get("content_length"),
                start_char=c.get("start_char"),
                end_char=c.get("end_char"),
            )
            self.db.add(row)
            rows.append(row)
        self.db.commit()
        for r in rows:
            self.db.refresh(r)
        return rows

    def get_chunks_by_resource(self, resource_ids: List[UUID]) -> List[ResourceChunk]:
        return (
            self.db.query(ResourceChunk)
            .filter(ResourceChunk.resource_id.in_(resource_ids))
            .order_by(ResourceChunk.chunk_index.asc().nulls_last())
            .all()
        )

    def vector_search(self, resource_ids: List[UUID], query_embedding: List[float], top_k: int = 10) -> List[dict]:
        """Perform ANN search using pgvector distance ordering."""
        if not resource_ids:
            return []
        placeholders = ", ".join([f":id{i}" for i in range(len(resource_ids))])
        sql = text(
            f"""
            SELECT id, resource_id, chunk_index, content, embedding_model
            FROM resource_chunks
            WHERE resource_id IN ({placeholders})
            ORDER BY embedding <-> :query_embedding
            LIMIT :top_k
            """
        )
        params = {f"id{i}": str(rid) for i, rid in enumerate(resource_ids)}
        params["query_embedding"] = query_embedding
        params["top_k"] = top_k
        result = self.db.execute(sql, params)
        return [dict(row) for row in result]
