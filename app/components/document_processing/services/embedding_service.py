# app/components/document_processing/services/embedding_service.py

from app.shared.ai.embeddings import generate_embedding
from app.components.document_processing.utils.text_cleaner import basic_clean
from app.components.document_processing.utils.chunker import chunk_text


async def generate_text_embedding(text: str) -> list[float]:
    """
    Component-specific text embedding logic:
    - Clean text
    - (Optional) Chunk text
    - Call the shared embedding generator
    """

    cleaned = basic_clean(text)
    # # Optional: chunking can be added here if needed
    # chunks = chunk_text(cleaned)
    vector = await generate_embedding(cleaned)

    return vector

async def embed_document_text(text: str) -> list[float]:
    """
    Generate embedding for the full extracted text.
    Later you can switch to chunk-based embeddings.
    """
    if not text or len(text.strip()) == 0:
        return []

    vector = await generate_embedding(text)  # Calls Gemini API
    return vector

async def embed_chunks(chunks: list[str]) -> list[dict]:
    results = []
    for idx, ch in enumerate(chunks):
        vec = await generate_text_embedding(ch)
        results.append({
            "chunk_id": idx,
            "text": ch,
            "embedding": vec
        })
    return results