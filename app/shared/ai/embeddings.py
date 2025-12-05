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

    if not text or not text.strip():
        return []

    try:
        response = genai.embed_content(
            model=EMBED_MODEL,
            content=text,
        )
    except Exception as e:
        # Log and return empty to avoid hard crashes
        print(f"[ERROR] Embedding failed: {e}")
        return []

    # Gemini returns: { "embedding": [...] }
    embedding = response.get("embedding")
    if not embedding:
        print("[WARN] No embedding returned from Gemini.")
        return []

    return embedding
