from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid

app = FastAPI(title="Sinhala ED API", version="0.1")

# --- bootstrap models & vector db ---
emb_model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
client = QdrantClient(host="localhost", port=6333)
COLL = "docs"

# ensure collection
if COLL not in [c.name for c in client.get_collections().collections]:
    client.recreate_collection(
        collection_name=COLL,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )

class AddDocIn(BaseModel):
    doc_id: str | None = None
    text: str
    meta: dict | None = None

class QueryIn(BaseModel):
    query: str
    top_k: int = 5

@app.post("/add_doc")
def add_doc(payload: AddDocIn):
    vid = payload.doc_id or str(uuid.uuid4())
    vec = emb_model.encode([payload.text])[0].tolist()
    client.upsert(
        collection_name=COLL,
        points=[PointStruct(id=vid, vector=vec, payload=payload.meta or {"len": len(payload.text)})]
    )
    return {"ok": True, "doc_id": vid}

@app.post("/search")
def search(payload: QueryIn):
    q = emb_model.encode([payload.query])[0].tolist()
    hits = client.search(collection_name=COLL, query_vector=q, limit=payload.top_k)
    return [{"id": h.id, "score": float(h.score), "meta": h.payload} for h in hits]

# simple grading: cosine similarity between student answer & gold key
class GradeIn(BaseModel):
    answer: str
    gold: str

@app.post("/grade")
def grade(payload: GradeIn):
    a, g = emb_model.encode([payload.answer, payload.gold])
    # cosine similarity for sentence-transformers is high=similar; normalize to %
    import numpy as np
    sim = float(np.dot(a, g) / (np.linalg.norm(a) * np.linalg.norm(g)))
    score = max(0.0, min(1.0, (sim + 1) / 2)) * 100  # map [-1,1] -> [0,100]
    feedback = "Good coverage" if score >= 80 else "Add missing key points"
    return {"score": round(score, 1), "feedback": feedback, "similarity": round(sim, 3)}
