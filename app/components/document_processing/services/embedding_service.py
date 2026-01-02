# app/components/document_processing/services/embedding_service.py

from typing import List, Dict, Optional

from app.shared.ai.embeddings import generate_embedding, EMBED_MODEL
from app.components.document_processing.utils.text_cleaner import basic_clean
from app.components.document_processing.utils.chunker import chunk_text


def generate_text_embedding(text: str) -> List[float]:
    cleaned = basic_clean(text)
    if not cleaned:
        return []
    return generate_embedding(cleaned)


def embed_document_text(text: str) -> List[float]:
    if not text or not text.strip():
        return []
    cleaned = basic_clean(text)
    if not cleaned:
        return []
    return generate_embedding(cleaned)


def embed_chunks(
    text: str,
    doc_id: Optional[str] = None,
    max_tokens: int = 300,
    overlap_tokens: int = 30
) -> List[Dict]:
    if not text or not text.strip():
        return []

    cleaned = basic_clean(text)
    chunk_list = chunk_text(
        cleaned,
        max_tokens=max_tokens,
        overlap_tokens=overlap_tokens
    )

    results = []

    for ch in chunk_list:
        c_text = ch["text"]
        c_id = ch["chunk_id"]
        c_numbering = ch.get("numbering")
        c_start = ch.get("start_char", 0)
        c_end = ch.get("end_char", len(c_text))

        vec = generate_embedding(c_text)

        global_id = f"{doc_id}_{c_id}" if doc_id else str(c_id)

        results.append({
            "chunk_id": c_id,
            "global_id": global_id,
            "text": c_text,
            "numbering": c_numbering,
            "embedding": vec,
            "embedding_model": EMBED_MODEL,
            "start_char": c_start,
            "end_char": c_end
        })

    return results
