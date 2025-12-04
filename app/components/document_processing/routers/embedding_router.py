# app/components/document_processing/routers/embedding_router.py

from fastapi import APIRouter
from app.components.document_processing.schemas.embedding_schema import (
    EmbeddingRequest,
    EmbeddingResponse,
)
from app.components.document_processing.services.embedding_service import (
    generate_text_embedding,
)

router = APIRouter()

@router.post("/embed", response_model=EmbeddingResponse)
async def embed_text(payload: EmbeddingRequest):
    """
    Generate embedding for given text.
    Currently returns dummy vector.
    Later: connect Gemini/text-embedding-004 etc.
    """
    vector = await generate_text_embedding(payload.text)
    return EmbeddingResponse(
        text=payload.text,
        embedding=vector,
        dimension=len(vector),
    )
