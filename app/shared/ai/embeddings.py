# app/shared/ai/embeddings.py

import threading
from app.core.gemini_client import GeminiClient
from app.core.config import settings
from google.genai import types
from sentence_transformers import SentenceTransformer, util
import huggingface_hub

if settings.HF_TOKEN:
    huggingface_hub.login(token=settings.HF_TOKEN, add_to_git_credential=False)

# Global semaphore to prevent CPU thrashing during heavy XLM-R math
# (One encoding task at a time per backend process)
ml_semaphore = threading.Semaphore(1)

# Global thread-safe cache for sentence embeddings
_embedding_cache = {}
_cache_lock = threading.Lock()


_xlmr = None
_xlmr_lock = threading.Lock()


def get_xlmr_model():
    global _xlmr
    if _xlmr is None:
        with _xlmr_lock:
            if _xlmr is None:
                _xlmr = SentenceTransformer(
                    "sentence-transformers/paraphrase-xlm-r-multilingual-v1"
                )
    return _xlmr

EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 768


def generate_embedding(text: str) -> list[float]:
    """
    Generate a 768-dim embedding using Gemini.
    """
    if not text or not text.strip():
        return []

    try:
        # Move client initialization inside to avoid startup crash if API keys missing
        client = GeminiClient.get_client()
        if not client:
            return []
            
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
        # Check cache first
        with _cache_lock:
            a_vec = _embedding_cache.get(a)
            b_vec = _embedding_cache.get(b)

        # Encode if missing (batching is preferred, but this is a fallback)
        if a_vec is None or b_vec is None:
            with ml_semaphore:
                if a_vec is None:
                    a_vec = get_xlmr_model().encode(a, convert_to_tensor=True)
                    with _cache_lock: _embedding_cache[a] = a_vec
                if b_vec is None:
                    b_vec = get_xlmr_model().encode(b, convert_to_tensor=True)
                    with _cache_lock: _embedding_cache[b] = b_vec

        sim = float(util.cos_sim(a_vec, b_vec))
        return min(sim * 1.2, 1.0)
    except Exception as e:
        print(f"[ERROR] Semantic similarity failed: {e}")
        return 0.5


def ensure_sentences_cached(sentences: list[str]):
    """
    Batch-encode multiple sentences into the global cache in one pass.
    Drastically faster than encoding one by one.
    """
    if not sentences:
        return

    # Deduplicate and filter already cached
    to_encode = []
    with _cache_lock:
        for s in set(sentences):
            if s and s.strip() and s not in _embedding_cache:
                to_encode.append(s)

    if not to_encode:
        return

    # Batch encode with semaphore
    print(f"[INFO] Batch encoding {len(to_encode)} new sentences...")
    with ml_semaphore:
        new_embs = get_xlmr_model().encode(
            to_encode, 
            batch_size=32, 
            convert_to_tensor=True,
            show_progress_bar=True
        )
        
        with _cache_lock:
            for i, s in enumerate(to_encode):
                _embedding_cache[s] = new_embs[i]
