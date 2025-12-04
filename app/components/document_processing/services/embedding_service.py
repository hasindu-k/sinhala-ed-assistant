# app/components/document_processing/services/embedding_service.py

import random

# Later: integrate real Gemini or Gecko embedding here

async def generate_text_embedding(text: str) -> list[float]:
    """
    Stub: returns a random 10-dim embedding.
    TODO:
    - Use Gemini / text-embedding-004
    - Call Google API
    """
    random.seed(42)  # deterministic for now
    return [random.random() for _ in range(10)]
