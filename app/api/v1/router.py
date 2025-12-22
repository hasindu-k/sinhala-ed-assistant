# app/api/v1/router.py
from fastapi import APIRouter

from app.components.voice_qa.routers.voice_router import router as voice_router
from app.routers import (
    chat_sessions,
    messages,
    resources,
    evaluation,
    rubrics,
    users,
    auth,
)

# Import routers from components
# from app.components.document_processing.routers.ocr_router import router as ocr_router
# from app.components.document_processing.routers.embedding_router import (
#     router as embedding_router,
# )
# from app.components.evaluation.routers.evaluation_router import (
#     router as evaluation_router,
# )
# from app.components.text_qa_summary.routers.qa_router import router as qa_router
# from app.components.voice_qa.routers.voice_router import router as voice_router

# Import Text Q&A Summary routers
from app.components.text_qa_summary.routers.chat_router import router as chat_router
from app.components.text_qa_summary.routers.resource_router import router as resource_router
from app.components.text_qa_summary.routers.text_qa_router import router as text_qa_router

api_router = APIRouter()

api_router.include_router(chat_sessions.router, prefix="/chat", tags=["Chat"])
api_router.include_router(messages.router, prefix="/messages", tags=["Messages"])
api_router.include_router(resources.router, prefix="/resources", tags=["Resources"])
api_router.include_router(evaluation.router, prefix="/evaluation-updated", tags=["Evaluation"])
api_router.include_router(rubrics.router, prefix="/rubrics", tags=["Rubrics"])
api_router.include_router(users.router, prefix="/users", tags=["Users"]) 
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"]) 

# Document Processing
# api_router.include_router(ocr_router, prefix="/document", tags=["Document Processing"])
# api_router.include_router(
#     embedding_router, prefix="/document", tags=["Document Embeddings"]
# )

# # Evaluation
# api_router.include_router(evaluation_router, prefix="/evaluation", tags=["Evaluation"])

# Voice Q&A
api_router.include_router(voice_router, prefix="/voice", tags=["Voice Q&A"])

# Text Q&A + Summary Component
api_router.include_router(chat_router, prefix="/text/chat", tags=["Chat Sessions"])
api_router.include_router(resource_router, prefix="/text/resource", tags=["Resources"])
api_router.include_router(text_qa_router, prefix="/text/qa", tags=["Text Q&A & Summary"])

print("✓ API Router configured with all components")
