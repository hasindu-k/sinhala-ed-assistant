# app/shared/ai/embeddings.py

from sentence_transformers import SentenceTransformer, util

# Load once globally
xlmr = SentenceTransformer(
    "sentence-transformers/paraphrase-xlm-r-multilingual-v1"
)

def semantic_similarity(a: str, b: str) -> float:
    """Compute cosine similarity with safe fallbacks."""
    if not a.strip() or not b.strip():
        return 0.0

    try:
        a_vec = xlmr.encode(a, convert_to_tensor=True)
        b_vec = xlmr.encode(b, convert_to_tensor=True)
        sim = float(util.cos_sim(a_vec, b_vec))
        return min(sim * 1.2, 1.0)
    except:
        return 0.5
