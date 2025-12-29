import faiss
import numpy as np

class VectorStore:
    def __init__(self, dim: int = 3072):  # text-embedding-004 dim
        self.index = faiss.IndexFlatL2(dim)
        self.chunks = []

    def add(self, embeddings, chunks):
        vectors = np.array(embeddings).astype("float32")
        self.index.add(vectors)
        self.chunks.extend(chunks)

    def search(self, query_vec, top_k=3):
        q = np.array([query_vec]).astype("float32")
        distances, indices = self.index.search(q, top_k)
        results = []
        for idx in indices[0]:
            results.append(self.chunks[idx])
        return results
