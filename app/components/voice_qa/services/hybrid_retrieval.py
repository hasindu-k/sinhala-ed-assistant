"""Hybrid retrieval pipeline placed under voice_qa for component locality.

This is the same hybrid retrieval implementation used elsewhere but colocated
with the voice QA component so imports are simpler and the component is
self-contained.
"""

from typing import List, Dict, Tuple, Optional
import numpy as np
from sqlalchemy import text

from app.core.database import engine
from app.components.document_processing.services.embedding_service import generate_text_embedding

try:
    # CrossEncoder from sentence-transformers
    from sentence_transformers.cross_encoder import CrossEncoder
except Exception:
    CrossEncoder = None


def lexical_retrieval(query: str, top_k: int = 50, config: str = "simple") -> List[Dict]:
    results: List[Dict] = []
    if not query or not query.strip():
        return results

    sql = text(
        """
        SELECT chunk_id, chunk_text, metadata,
               ts_rank_cd(to_tsvector(:cfg, chunk_text), plainto_tsquery(:cfg, :q)) AS rank
        FROM document_chunks
        WHERE to_tsvector(:cfg, chunk_text) @@ plainto_tsquery(:cfg, :q)
        ORDER BY rank DESC
        LIMIT :k
        """
    )

    try:
        with engine.connect() as conn:
            rows = conn.execute(sql, {"cfg": config, "q": query, "k": top_k}).fetchall()
            for r in rows:
                results.append({
                    "chunk_id": r[0],
                    "text": r[1],
                    "metadata": r[2],
                    "rank": float(r[3]) if r[3] is not None else 0.0,
                })
    except Exception as e:
        print(f"[voice_qa.hybrid_retrieval] lexical_retrieval DB error: {e}")

    return results


def normalize_vector(vec: List[float]) -> Optional[List[float]]:
    if not vec:
        return None
    a = np.array(vec, dtype=np.float32)
    norm = np.linalg.norm(a)
    if norm == 0:
        return a.tolist()
    return (a / norm).tolist()


def dense_retrieval(query_embedding: List[float], top_k: int = 50) -> List[Dict]:
    results: List[Dict] = []
    if not query_embedding:
        return results

    q_norm = normalize_vector(query_embedding)
    if q_norm is None:
        return results

    sql = text(
        """
        SELECT chunk_id, chunk_text, metadata, embedding <-> :vec AS distance
        FROM document_chunks
        ORDER BY distance ASC
        LIMIT :k
        """
    )

    try:
        with engine.connect() as conn:
            rows = conn.execute(sql, {"vec": q_norm, "k": top_k}).fetchall()
            for r in rows:
                results.append({
                    "chunk_id": r[0],
                    "text": r[1],
                    "metadata": r[2],
                    "distance": float(r[3]) if r[3] is not None else None,
                })
    except Exception as e:
        print(f"[voice_qa.hybrid_retrieval] dense_retrieval DB error: {e}")

    return results


def merge_candidates(lexical: List[Dict], dense: List[Dict], pool_size: int = 100) -> List[Dict]:
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


class CrossEncoderReranker:
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-xlm-r-multilingual-v1"):
        if CrossEncoder is None:
            raise RuntimeError("CrossEncoder is not available. Install sentence-transformers with CrossEncoder support.")
        self.model_name = model_name
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, candidates: List[Dict], top_k: int = 5) -> List[Dict]:
        if not candidates:
            return []

        pairs = [(query, c.get("text", "")) for c in candidates]
        try:
            scores = self.model.predict(pairs)
        except Exception as e:
            print(f"[voice_qa.hybrid_retrieval] cross-encoder prediction failed: {e}")
            return candidates[:top_k]

        scored = []
        for c, s in zip(candidates, scores):
            c_copy = c.copy()
            c_copy["score"] = float(s)
            scored.append(c_copy)

        scored.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        return scored[:top_k]


def retrieve_top_k(
    query: str,
    top_k: int = 5,
    lexical_k: int = 50,
    dense_k: int = 50,
    candidate_pool: int = 100,
    reranker_model: Optional[str] = None,
) -> List[Dict]:
    lexical = lexical_retrieval(query, top_k=lexical_k)

    q_emb = generate_text_embedding(query)
    if not q_emb:
        dense = []
    else:
        dense = dense_retrieval(q_emb, top_k=dense_k)

    candidates = merge_candidates(lexical, dense, pool_size=candidate_pool)

    if reranker_model is None:
        reranker_model = "sentence-transformers/paraphrase-xlm-r-multilingual-v1"

    try:
        reranker = CrossEncoderReranker(reranker_model)
        final = reranker.rerank(query, candidates, top_k=top_k)
    except Exception as e:
        print(f"[voice_qa.hybrid_retrieval] reranker init failed, returning merged top_k: {e}")
        final = candidates[:top_k]

    return final
