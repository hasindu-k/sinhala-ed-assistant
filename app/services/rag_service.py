from typing import List, Dict, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.services.resource_chunk_service import ResourceChunkService
from app.services.message_context_service import MessageContextService
from app.services.message_service import MessageService


class RAGService:
    """RAG orchestration: retrieve chunks, log sources, create assistant message."""

    def __init__(self, db: Session):
        self.db = db
        self.chunk_service = ResourceChunkService(db)
        self.context_service = MessageContextService(db)
        self.message_service = MessageService(db)

    def generate_response(
        self,
        session_id: UUID,
        user_message_id: UUID,
        user_query: str,
        resource_ids: List[UUID],
        query_embedding: Optional[List[float]] = None,
        top_k: int = 8,
    ) -> Dict:
        """
        1. Retrieve top-k chunks via vector search (if embedding provided) or simple retrieval
        2. Log used chunks into message_context_chunks
        3. Create assistant message (content generation mocked here)
        4. Return assistant message payload + sources
        """
        if query_embedding is not None:
            hits = self.chunk_service.vector_search(resource_ids, query_embedding, top_k)
        else:
            # Fallback: return first N chunks across resources
            all_chunks = self.chunk_service.get_chunks_by_resource(resource_ids)
            hits = [
                {
                    "id": ch.id,
                    "resource_id": ch.resource_id,
                    "chunk_index": ch.chunk_index,
                    "content": ch.content,
                    "embedding_model": ch.embedding_model,
                }
                for ch in all_chunks[:top_k]
            ]

        # Log sources
        self.context_service.log_used_chunks(
            user_message_id,
            [
                {
                    "chunk_id": h["id"] if isinstance(h, dict) else h["id"],
                    "similarity_score": None,
                    "rank": i + 1,
                }
                for i, h in enumerate(hits)
            ],
        )

        # Mock generation (replace with actual LLM call):
        context_snippets = "\n\n".join((h["content"] if isinstance(h, dict) else h["content"]) or "" for h in hits)
        draft_answer = f"Answer based on retrieved context:\n\n{context_snippets}\n\nUser query: {user_query}"

        assistant_msg = self.message_service.create_assistant_message(
            session_id=session_id,
            content=draft_answer,
            model_info={"model_name": "GPT-5"},
        )

        return {
            "assistant_message_id": assistant_msg.id,
            "content": assistant_msg.content,
            "sources": hits,
        }
