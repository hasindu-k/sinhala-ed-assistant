# app/components/text_qa_summary/routers/qa_router.py

from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Health check endpoint for QA component.
    """
    return {"status": "QA component is healthy."}