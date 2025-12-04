from fastapi import APIRouter
from app.components.voice_qa.routes import router as voice_router

api_router = APIRouter()

api_router.include_router(voice_router)
