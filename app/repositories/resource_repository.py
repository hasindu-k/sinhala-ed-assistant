# app/repositories/resource_repository.py

from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.shared.models.resource_file import ResourceFile


class ResourceRepository:
    """Data access for ResourceFile."""

    def __init__(self, db: Session):
        self.db = db

    def upload_resource(
        self,
        user_id: UUID,
        original_filename: Optional[str],
        storage_path: Optional[str],
        mime_type: Optional[str],
        size_bytes: Optional[int],
        source_type: Optional[str] = None,
        language: Optional[str] = None,
    ) -> ResourceFile:
        res = ResourceFile(
            user_id=user_id,
            original_filename=original_filename,
            storage_path=storage_path,
            mime_type=mime_type,
            size_bytes=size_bytes,
            source_type=source_type,
            language=language,
        )
        self.db.add(res)
        self.db.commit()
        self.db.refresh(res)
        return res

    def get_resource(self, resource_id: UUID) -> Optional[ResourceFile]:
        return self.db.query(ResourceFile).filter(ResourceFile.id == resource_id).first()

    def list_user_resources(self, user_id: UUID) -> List[ResourceFile]:
        return (
            self.db.query(ResourceFile)
            .filter(ResourceFile.user_id == user_id)
            .order_by(ResourceFile.created_at.desc())
            .all()
        )

    def vector_search_documents(
        self, 
        resource_ids: List[UUID], 
        query_embedding: List[float], 
        top_k: int = 5
    ) -> List[dict]:
        """
        First-stage retrieval: Find top-K most relevant documents using document embeddings.
        This is much faster than searching all chunks.
        
        Args:
            resource_ids: List of resource IDs to search within
            query_embedding: Query embedding vector
            top_k: Number of top documents to return
            
        Returns:
            List of dicts with resource_id and similarity_score
        """
        if not resource_ids:
            return []
            
        placeholders = ", ".join([f":id{i}" for i in range(len(resource_ids))])
        sql = text(
            f"""
            SELECT 
                id as resource_id,
                original_filename,
                1 - (document_embedding <=> :query_embedding) as similarity_score
            FROM resource_files
            WHERE id IN ({placeholders})
                AND document_embedding IS NOT NULL
            ORDER BY document_embedding <=> :query_embedding
            LIMIT :top_k
            """
        )
        
        params = {f"id{i}": str(rid) for i, rid in enumerate(resource_ids)}
        params["query_embedding"] = query_embedding
        params["top_k"] = top_k
        
        result = self.db.execute(sql, params)
        return [dict(row) for row in result]

    def list_resources_by_ids(self, resource_ids: List[UUID]) -> List[ResourceFile]:
        """List resources by their IDs."""
        return (
            self.db.query(ResourceFile)
            .filter(ResourceFile.id.in_(resource_ids))
            .all()
        ) 