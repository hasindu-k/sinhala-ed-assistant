# app/services/semantic_similarity_service.py
import numpy as np
from typing import List, Tuple
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

    @staticmethod
    def compute_pairwise_similarities(sentences_a: List[str], sentences_b: List[str]) -> np.ndarray:
        """
        Compute cosine similarity between all pairs in two sets of sentences.
        Returns a matrix of shape (len(sentences_a), len(sentences_b))
        """
        if not sentences_a or not sentences_b:
            return np.array([])

        # Batch embed all sentences at once
        embs_a = EmbeddingService.embed_batch(sentences_a)
        embs_b = EmbeddingService.embed_batch(sentences_b)

        # Compute all pairwise similarities at once using matrix multiplication
        # Shape: (len_a, embedding_dim) @ (embedding_dim, len_b) -> (len_a, len_b)
        similarities = np.dot(embs_a, embs_b.T)
        
        return similarities

    @staticmethod
    def similarity_batch(pairs: List[Tuple[str, str]]) -> List[float]:
        """Compute similarity for multiple text pairs efficiently"""
        if not pairs:
            return []

        # Separate all texts for batch embedding
        texts_a = [pair[0] for pair in pairs if pair[0] and pair[1]]
        texts_b = [pair[1] for pair in pairs if pair[0] and pair[1]]

        if not texts_a:
            return [0.0] * len(pairs)

        # Batch embed all texts at once
        embs_a = EmbeddingService.embed_batch(texts_a)
        embs_b = EmbeddingService.embed_batch(texts_b)

        # Compute similarities
        similarities = []
        for emb_a, emb_b in zip(embs_a, embs_b):
            similarities.append(float(np.dot(emb_a, emb_b)))

        return similarities