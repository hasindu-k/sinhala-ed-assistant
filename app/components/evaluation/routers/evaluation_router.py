# app/components/evaluation/routers/evaluation_router.py

from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Health check endpoint for Evaluation component.
    """
    return {"status": "Evaluation component is healthy."}

