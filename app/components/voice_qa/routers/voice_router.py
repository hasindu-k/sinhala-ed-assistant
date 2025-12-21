# app/components/voice_qa/routers/voice_router.py

from fastapi import APIRouter, UploadFile, File, Form
from uuid import UUID

from app.components.voice_qa.services.hybrid_retrieval import retrieve_top_k
from app.components.voice_qa.services.whisper_service import (
    VoiceService,
    VoiceQAService,
)
from app.services.audio_storage import upload_audio_to_firebase
from app.services.chat_service import save_chat_message
from app.components.voice_qa.services.context_service import get_allowed_resource_ids
from app.core.database import get_db

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
        "standard": standard,
    }


# The heavier pipeline helpers live in `VoiceQAService` (in whisper_service.py).


@router.post("/qa")
async def qa_from_voice(
    audio: UploadFile = File(...),
    session_id: str = Form(...),
    top_k: int = 3,
):
    # Save audio temporarily
    temp_path = "temp.wav"
    with open(temp_path, "wb") as f:
        f.write(await audio.read())

    # Upload to Firebase
    audio_url = upload_audio_to_firebase(temp_path)

    # Transcribe
    raw_text = VoiceService.transcribe_audio(temp_path)
    normalized, standard = VoiceService.standardize_southern_sinhala(raw_text)
    question_text = standard or normalized or raw_text

    # Save USER message (get message_id)
    user_message_id = save_chat_message(
    session_id=UUID(session_id),
    role="user",
    modality="voice",
    content=question_text,      # standardized text
    transcript=raw_text,        # raw whisper output
    audio_url=audio_url,
    )

    # Resolve allowed resources
    db = next(get_db())
    allowed_resource_ids = get_allowed_resource_ids(
        db=db,
        session_id=UUID(session_id),
        message_id=user_message_id,
    )

    # RAG
    top_chunks = retrieve_top_k(
    query=question_text,
    resource_ids=allowed_resource_ids,
    top_k=top_k,
    )

    prompt = VoiceQAService.build_prompt(question_text, top_chunks)
    answer = VoiceQAService.llm_generate(prompt)

    # Save ASSISTANT message
    save_chat_message(
    session_id=UUID(session_id),
    role="assistant",
    modality="text",
    content=answer,
    )


    return {
        "question": question_text,
        "retrieved_chunks": top_chunks,
        "answer": answer,
    }