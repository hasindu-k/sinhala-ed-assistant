# app/services/rag_service.py

from typing import List, Dict, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.services.resource_chunk_service import ResourceChunkService
from app.services.message_context_service import MessageContextService
from app.services.message_service import MessageService
from app.repositories.resource_repository import ResourceRepository


class RAGService:
    """RAG orchestration with two-stage retrieval: document filtering → chunk search."""

    def __init__(self, db: Session):
        self.db = db
        self.chunk_service = ResourceChunkService(db)
        self.context_service = MessageContextService(db)
        self.message_service = MessageService(db)
        self.resource_repository = ResourceRepository(db)

    def generate_response(
        self,
        session_id: UUID,
        user_message_id: UUID,
        user_query: str,
        resource_ids: List[UUID],
        query_embedding: Optional[List[float]] = None,
        top_k: int = 8,
        top_n_docs: int = 3,  # Number of documents to filter to
    ) -> Dict:
        """
        Two-stage retrieval:
        1. Find top-N most relevant documents using document embeddings (fast filtering)
        2. Search chunks only within those N documents (focused retrieval)
        3. Log used chunks and create assistant message
        
        Args:
            session_id: Chat session ID
            user_message_id: User message ID for context tracking
            user_query: User's query text
            resource_ids: List of resource IDs to search
            query_embedding: Query embedding vector
            top_k: Number of chunks to retrieve from filtered documents
            top_n_docs: Number of documents to filter to in stage 1
        """
        # TODO: move vector_search client/model selection into config to vary per tenant
        if query_embedding is not None:
            # Stage 1: Find top-N documents using document embeddings
            top_documents = self.resource_repository.vector_search_documents(
                resource_ids=resource_ids,
                query_embedding=query_embedding,
                top_k=top_n_docs
            )
            
            if top_documents:
                # Extract resource IDs from top documents
                filtered_resource_ids = [doc["resource_id"] for doc in top_documents]
                
                # Stage 2: Search chunks only within top documents
                hits = self.chunk_service.vector_search(
                    resource_ids=filtered_resource_ids,
                    query_embedding=query_embedding,
                    top_k=top_k
                )
            else:
                # Fallback if no documents have embeddings
                hits = self.chunk_service.vector_search(
                    resource_ids=resource_ids,
                    query_embedding=query_embedding,
                    top_k=top_k
                )
        else:
            # Fallback: return first N chunks across resources (no embedding provided)
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
        # TODO: persist similarity_score once vector store returns it for traceability
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

        # TODO: replace mock generation with actual LLM call and streaming support
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

