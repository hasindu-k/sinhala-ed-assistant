import numpy as np
from app.services.embedding_service import EmbeddingService


class SemanticSimilarityService:
    @staticmethod
    def similarity(text_a: str, text_b: str) -> float:
        if not text_a or not text_b:
            return 0.0

        emb_a = EmbeddingService.embed(text_a)
        emb_b = EmbeddingService.embed(text_b)

        # cosine similarity (already normalized)
        return float(np.dot(emb_a, emb_b))
