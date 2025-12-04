# app/components/voice_qa/routers/voice_router.py

from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Health check endpoint for Voice component.
    """
    return {"status": "Voice component is healthy."}