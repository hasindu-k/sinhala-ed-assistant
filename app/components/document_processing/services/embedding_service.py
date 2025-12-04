# app/components/document_processing/services/embedding_service.py

from app.shared.ai.embeddings import generate_embedding
from app.components.document_processing.utils.text_cleaner import basic_clean
# from app.components.document_processing.utils.chunker import chunk_text


async def generate_text_embedding(text: str) -> list[float]:
    """
    Component-specific text embedding logic:
    - Clean text
    - (Optional) Chunk text
    - Call the shared embedding generator
    """

    cleaned = basic_clean(text)
    vector = generate_embedding(cleaned)

    return vector
