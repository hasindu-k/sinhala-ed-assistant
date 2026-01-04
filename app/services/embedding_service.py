from sentence_transformers import SentenceTransformer
import numpy as np

class EmbeddingService:
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            # Multilingual model works well for Sinhala
            cls._model = SentenceTransformer(
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            )
        return cls._model

    @classmethod
    def embed(cls, text: str) -> np.ndarray:
        model = cls.get_model()
        return model.encode(text, normalize_embeddings=True)
