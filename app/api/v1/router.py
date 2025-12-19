# app/api/v1/router.py

from fastapi import APIRouter

from app.routers import (
    chat_sessions,
    messages,
    resources,
    evaluation,
    rubrics
)

# Import routers from components
from app.components.document_processing.routers.ocr_router import router as ocr_router
from app.components.document_processing.routers.embedding_router import (
    router as embedding_router,
)
from app.components.evaluation.routers.evaluation_router import (
    router as evaluation_router,
)
from app.components.text_qa_summary.routers.qa_router import router as qa_router
from app.components.voice_qa.routers.voice_router import router as voice_router

api_router = APIRouter()

api_router.include_router(chat_sessions.router, prefix="/chat", tags=["Chat"])
api_router.include_router(messages.router, prefix="/messages", tags=["Messages"])
api_router.include_router(resources.router, prefix="/resources", tags=["Resources"])
api_router.include_router(evaluation.router, prefix="/evaluation-updated", tags=["Evaluation"])
api_router.include_router(rubrics.router, prefix="/rubrics", tags=["Rubrics"])

# Document Processing
api_router.include_router(ocr_router, prefix="/document", tags=["Document Processing"])
api_router.include_router(
    embedding_router, prefix="/document", tags=["Document Embeddings"]
)

# Evaluation
api_router.include_router(evaluation_router, prefix="/evaluation", tags=["Evaluation"])

# Text Q&A + Summary
api_router.include_router(qa_router, prefix="/text", tags=["Text Q&A & Summary"])

# Voice Q&A
api_router.include_router(voice_router, prefix="/voice", tags=["Voice Q&A"])
