# app/components/document_processing/schemas/embedding_schema.py

from pydantic import BaseModel

class EmbeddingRequest(BaseModel):
    text: str

class EmbeddingResponse(BaseModel):
    text: str
    embedding: list[float]
    dimension: int
