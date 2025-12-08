# app/components/voice_qa/routers/voice_router.py

from fastapi import APIRouter, UploadFile, File
from app.components.voice_qa.whisper_service import VoiceService

router = APIRouter()

# @router.get("/health")
# async def health_check():
#     """
#     Health check endpoint for Voice component.
#     """
#     return {"status": "Voice component is healthy."}


@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):

    temp_path = "temp.wav"
    with open(temp_path, "wb") as f:
        f.write(await audio.read())

    raw_text = VoiceService.transcribe_audio(temp_path)
    normalized, standard = VoiceService.standardize_southern_sinhala(raw_text)

    return {
        "raw": raw_text,
        "normalized": normalized,
        "standard": standard
    }