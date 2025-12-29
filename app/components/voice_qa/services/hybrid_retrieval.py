"""
Hybrid retrieval pipeline scoped by allowed resource_ids.

This implementation strictly limits retrieval to:
- message-level attachments, OR
- session-level resources

This prevents hallucinations from unrelated documents.
"""

from typing import List, Dict, Optional
import numpy as np
from sqlalchemy import text

from app.core.database import engine
from app.components.document_processing.services.embedding_service import generate_text_embedding

try:
    from sentence_transformers.cross_encoder import CrossEncoder
except Exception:
    CrossEncoder = None


# ---------------------------------------------------------
# Utilities
# ---------------------------------------------------------

def normalize_vector(vec: List[float]) -> Optional[List[float]]:
    if not vec:
        return None
    a = np.array(vec, dtype=np.float32)
    norm = np.linalg.norm(a)
    if norm == 0:
        return a.tolist()
    return (a / norm).tolist()


# ---------------------------------------------------------
# Lexical retrieval (SCOPED)
# ---------------------------------------------------------

def lexical_retrieval(
    query: str,
    resource_ids: List[str],
    top_k: int = 50,
    config: str = "simple",
) -> List[Dict]:
    if not query or not resource_ids:
        return []

    sql = text(
        """
        SELECT
            id,
            content,
            ts_rank_cd(
                to_tsvector(:cfg, content),
                plainto_tsquery(:cfg, :q)
            ) AS rank
        FROM resource_chunks
        WHERE resource_id = ANY(:resource_ids)
          AND to_tsvector(:cfg, content) @@ plainto_tsquery(:cfg, :q)
        ORDER BY rank DESC
        LIMIT :k
        """
    )

    results = []

    with engine.connect() as conn:
        rows = conn.execute(
            sql,
            {
                "cfg": config,
                "q": query,
                "k": top_k,
                "resource_ids": resource_ids,
            },
        ).fetchall()

        for r in rows:
            results.append({
                "chunk_id": r.id,
                "text": r.content,   # normalize key name
                "rank": float(r.rank) if r.rank else 0.0,
            })

    return results


# ---------------------------------------------------------
# Dense retrieval (SCOPED)
# ---------------------------------------------------------

def dense_retrieval(
    query_embedding: List[float],
    resource_ids: List[str],
    top_k: int = 50,
) -> List[Dict]:
    if not query_embedding or not resource_ids:
        return []

    q_norm = normalize_vector(query_embedding)
    if q_norm is None:
        return []

    sql = text(
    """
    SELECT
        id,
        content,
        embedding <-> (:vec)::vector AS distance
    FROM resource_chunks
    WHERE resource_id = ANY(:resource_ids)
    ORDER BY distance ASC
    LIMIT :k
    """
    )


    results = []

    with engine.connect() as conn:
        rows = conn.execute(
            sql,
            {
                "vec": q_norm,
                "k": top_k,
                "resource_ids": resource_ids,
            },
        ).fetchall()

        for r in rows:
            results.append({
                "chunk_id": r.id,
                "text": r.content,
                "distance": float(r.distance),
            })

    return results


# ---------------------------------------------------------
# Candidate merge
# ---------------------------------------------------------

def merge_candidates(
    lexical: List[Dict],
    dense: List[Dict],
    pool_size: int = 100,
) -> List[Dict]:
    merged: List[Dict] = []
    seen = set()

    for src in (lexical, dense):
        for item in src:
            cid = item.get("chunk_id")
            if cid in seen:
                continue
            merged.append(item)
            seen.add(cid)
            if len(merged) >= pool_size:
                return merged

    return merged


# ---------------------------------------------------------
# Cross-encoder reranker
# ---------------------------------------------------------

class CrossEncoderReranker:
    def __init__(self, model_name: str):
        if CrossEncoder is None:
            raise RuntimeError("CrossEncoder not available")
        self.model = CrossEncoder(model_name)

    def rerank(
        self,
        query: str,
        candidates: List[Dict],
        top_k: int,
    ) -> List[Dict]:
        if not candidates:
            return []

        pairs = [(query, c["text"]) for c in candidates]

        try:
            scores = self.model.predict(pairs)
        except Exception as e:
            print(f"[voice_qa.hybrid_retrieval] rerank failed: {e}")
            return candidates[:top_k]

        scored = []
        for c, s in zip(candidates, scores):
            c2 = c.copy()
            c2["score"] = float(s)
            scored.append(c2)

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]


# ---------------------------------------------------------
# Public API (SCOPED)
# ---------------------------------------------------------

def retrieve_top_k(
    *,
    query: str,
    resource_ids: List[str],
    top_k: int = 5,
    lexical_k: int = 50,
    dense_k: int = 50,
    candidate_pool: int = 100,
    reranker_model: Optional[str] = None,
) -> List[Dict]:
    """
    Retrieve top-k chunks ONLY from allowed resource_ids.
    """

    if not resource_ids:
        return []

    lexical = lexical_retrieval(
        query=query,
        resource_ids=resource_ids,
        top_k=lexical_k,
    )

    q_emb = generate_text_embedding(query)
    dense = dense_retrieval(
        query_embedding=q_emb,
        resource_ids=resource_ids,
        top_k=dense_k,
    ) if q_emb else []

    candidates = merge_candidates(lexical, dense, pool_size=candidate_pool)

    if not candidates:
        return []

    model = reranker_model or "sentence-transformers/paraphrase-xlm-r-multilingual-v1"

    try:
        reranker = CrossEncoderReranker(model)
        return reranker.rerank(query, candidates, top_k)
    except Exception as e:
        print(f"[voice_qa.hybrid_retrieval] reranker unavailable: {e}")
        return candidates[:top_k]
