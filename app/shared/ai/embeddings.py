# app/shared/ai/embeddings.py

from app.core.gemini_client import GeminiClient
from google.genai import types
from sentence_transformers import SentenceTransformer, util

# Load local semantic model once
xlmr = SentenceTransformer(
    "sentence-transformers/paraphrase-xlm-r-multilingual-v1"
)

client = GeminiClient.get_client()

EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 768


def generate_embedding(text: str) -> list[float]:
    """
    Generate a 768-dim embedding using Gemini.
    """
    if not text or not text.strip():
        return []

    try:
        result = client.models.embed_content(
            model=EMBED_MODEL,
            contents=text,
            config=types.EmbedContentConfig(
                output_dimensionality=EMBED_DIM
            )
        )

        if result.embeddings:
            return result.embeddings[0].values

        return []

    except Exception as e:
        print(f"[ERROR] Gemini Embedding failed: {e}")
        return []


def semantic_similarity(a: str, b: str) -> float:
    """
    Compute cosine similarity using local XLM-R
    (fast, offline, safe fallback).
    """
    if not a.strip() or not b.strip():
        return 0.0

    try:
        a_vec = xlmr.encode(a, convert_to_tensor=True)
        b_vec = xlmr.encode(b, convert_to_tensor=True)
        sim = float(util.cos_sim(a_vec, b_vec))
        return min(sim * 1.2, 1.0)

    except Exception as e:
        print(f"[ERROR] Semantic similarity failed: {e}")
        return 0.5
