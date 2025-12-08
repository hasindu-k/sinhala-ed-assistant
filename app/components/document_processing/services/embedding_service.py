# app/components/document_processing/services/embedding_service.py
from typing import List, Dict

from app.shared.ai.embeddings import generate_embedding
from app.components.document_processing.utils.text_cleaner import basic_clean
from app.components.document_processing.utils.chunker import chunk_text


def generate_text_embedding(text: str) -> List[float]:
    """
    Clean and embed text using Gemini.
    """
    cleaned = basic_clean(text)
    if not cleaned:
        return []

    return generate_embedding(cleaned)


def embed_document_text(text: str) -> List[float]:
    """
    Generate full-document embedding.
    """
    if not text or not text.strip():
        return []

    cleaned = basic_clean(text)
    if not cleaned:
        return []

    return generate_embedding(cleaned)


def embed_chunks(
    text: str,
    doc_id: str,
    max_tokens: int = 300,
    overlap_tokens: int = 30
) -> List[Dict]:
    """
    Chunk text → embed each chunk → add metadata.

    Returns:
    [
      {
        "chunk_id": 0,
        "global_id": "<doc_id>_0",
        "text": "...",
        "numbering": "1.1",
        "embedding": [...]
      }
    ]
    """

    if not text or not text.strip():
        return []

    cleaned = basic_clean(text)

    # chunk_text returns: [{chunk_id, text, numbering}]
    chunk_list = chunk_text(cleaned, max_tokens=max_tokens, overlap_tokens=overlap_tokens)

    results = []

    for ch in chunk_list:
        c_text = ch["text"]
        c_id = ch["chunk_id"]
        c_numbering = ch.get("numbering")

        vec = generate_embedding(c_text)

        results.append({
            "chunk_id": c_id,
            "global_id": f"{doc_id}_{c_id}",
            "text": c_text,
            "numbering": c_numbering,
            "embedding": vec
        })

    return results
