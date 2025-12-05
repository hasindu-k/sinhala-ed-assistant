# app/components/document_processing/services/embedding_service.py
from typing import List, Dict

from app.shared.ai.embeddings import generate_embedding
from app.components.document_processing.utils.text_cleaner import basic_clean
from app.components.document_processing.utils.chunker import chunk_text


def generate_text_embedding(text: str) -> List[float]:
    """
    Component-specific text embedding logic:
    - Clean text
    - Call the shared embedding generator
    """

    cleaned = basic_clean(text)
    if not cleaned:
        return []

    vector = generate_embedding(cleaned)
    return vector


def embed_document_text(text: str) -> List[float]:
    """
    Generate embedding for the full extracted text.
    This is useful for:
    - global similarity
    - quick "overall document" search
    """

    if not text or not text.strip():
        return []

    cleaned = basic_clean(text)
    if not cleaned:
        return []

    vector = generate_embedding(cleaned)
    return vector


def embed_chunks(
    text: str,
    max_tokens: int = 300,
    overlap_tokens: int = 30,
) -> List[Dict]:
    """
    Generate embeddings for text chunks.

    Steps:
    - Clean the full text
    - Chunk it into ~max_tokens segments
    - Generate embedding per chunk
    - Return list of {chunk_id, text, embedding}
    """

    if not text or not text.strip():
        return []

    cleaned = basic_clean(text)
    if not cleaned:
        return []

    chunks = chunk_text(cleaned, max_tokens=max_tokens, overlap_tokens=overlap_tokens)

    results: List[Dict] = []
    for idx, ch in enumerate(chunks):
        if not ch.strip():
            continue

        # We can call generate_embedding directly because `chunks` are already cleaned.
        vec = generate_embedding(ch)

        results.append(
            {
                "chunk_id": idx,
                "text": ch,
                "embedding": vec,
            }
        )

    return results
