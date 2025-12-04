# app/shared/ai/embeddings.py

import google.generativeai as genai
from config.settings import settings

# Configure once
genai.configure(api_key=settings.EMBEDDING_API_KEY)

# Gemini embedding model
EMBED_MODEL = "models/text-embedding-004"


def generate_embedding(text: str) -> list[float]:
    """
    Generates an embedding using Gemini text-embedding-004.
    This is the central shared function used by all services.
    """
    response = genai.embed_content(
        model=EMBED_MODEL,
        content=text,
    )

    # Gemini returns: { embedding: [...] }
    return response["embedding"]
