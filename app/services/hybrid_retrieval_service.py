# app/services/hybrid_retrieval_service.py

from typing import List, Dict
from uuid import UUID
from rank_bm25 import BM25Okapi
import re

from app.services.resource_chunk_service import ResourceChunkService
from app.services.resource_service import ResourceService


class HybridRetrievalService:
    """
    Hybrid retrieval combining:
    1. Document embeddings
    2. BM25 lexical filtering
    3. Chunk embeddings (dense semantic search)
    """

    def __init__(self, db):
        self.db = db
        self.chunk_service = ResourceChunkService(db)
        self.resource_service = ResourceService(db)

    def _tokenize_sinhala(self, text: str) -> List[str]:
        """Simple Sinhala-friendly tokenizer: keeps words, removes punctuation."""
        return re.findall(r"[අ-෴]+", text)

    def retrieve(
        self,
        resource_ids: List[UUID],
        query: str,
        query_embedding: List[float],
        bm25_k: int = 10,      # top documents for BM25 fallback
        final_k: int = 8,      # top chunks after dense re-rank
        top_doc_k: int = 5,    # top documents from document embeddings
    ) -> List[Dict]:
        """
        Step 1: Filter top documents using document embeddings
        Step 2: Fallback to BM25 if no document embeddings exist
        Step 3: Retrieve chunks from top documents
        Step 4: Dense search on chunk embeddings
        """

        # -----------------------------
        # 1. Load all resources/documents
        # -----------------------------
        resources = self.resource_service.list_resources_by_ids(resource_ids)
        if not resources:
            return []

        # Separate resources with and without document embeddings
        resources_with_emb = [r for r in resources if r.document_embedding is not None]
        resources_without_emb = [r for r in resources if r.document_embedding is None]

        top_resource_ids = []

        # -----------------------------
        # 2. Filter top documents using document embeddings
        # -----------------------------
        if resources_with_emb:
            resource_ids_with_emb = [r.id for r in resources_with_emb]

            top_docs = self.search_documents(
                resource_ids=resource_ids_with_emb,
                query_embedding=query_embedding,
                top_k=top_doc_k
            )

            top_resource_ids.extend(
                [doc["resource_id"] for doc in top_docs]
            )

        # -----------------------------
        # 3. BM25 fallback for documents without embeddings
        # -----------------------------
        if not top_resource_ids and resources_without_emb:
            corpus = [self._tokenize_sinhala(r.original_filename or "") for r in resources_without_emb]
            bm25 = BM25Okapi(corpus)
            query_tokens = self._tokenize_sinhala(query)
            scores = bm25.get_scores(query_tokens)
            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:bm25_k]
            top_resource_ids.extend([resources_without_emb[i].id for i in top_indices])

        if not top_resource_ids:
            return []

        # -----------------------------
        # 4. Retrieve all chunks from top documents
        # -----------------------------
        top_chunks = self.chunk_service.get_chunks_by_resource(top_resource_ids)
        if not top_chunks:
            return []

        # -----------------------------
        # 5. Dense re-ranking on chunk embeddings
        # -----------------------------
        dense_hits = self.chunk_service.vector_search(
            resource_ids=top_resource_ids,
            query_embedding=query_embedding,
            top_k=final_k,
        )

        # -----------------------------
        # 6. Fallback if vector search returns nothing
        # -----------------------------
        if not dense_hits:
            top_chunks = self.chunk_service.get_chunks_by_resource(top_resource_ids)

            dense_hits = [
                {
                    "id": ch.id,
                    "resource_id": ch.resource_id,
                    "chunk_index": ch.chunk_index,
                    "content": ch.content,
                    "embedding_model": ch.embedding_model,
                    "similarity": None,
                    "rank": i + 1,
                }
                for i, ch in enumerate(top_chunks[:final_k])
            ]
        else:
            # attach rank for logging
            dense_hits = [{**h, "rank": i + 1} for i, h in enumerate(dense_hits)]

        return dense_hits
