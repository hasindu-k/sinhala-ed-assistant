# app/components/voice_qa/routers/voice_router.py

from fastapi import APIRouter, UploadFile, File, Form
from uuid import UUID

from typing import Optional
from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
import subprocess
import os


from app.components.voice_qa.services.hybrid_retrieval import retrieve_top_k
from app.components.voice_qa.services.whisper_service import (
    VoiceService,
    VoiceQAService,
)
from app.services.audio_storage import upload_audio_to_firebase
from app.services.chat_service import save_chat_message
from app.components.voice_qa.services.context_service import get_allowed_resource_ids
from app.components.voice_qa.services.context_service import attach_resource_to_message
from app.core.database import get_db
from app.shared.models.user import User
from app.core.security import get_current_user
from app.services.chat_session_service import ChatSessionService
from app.services.message_service import MessageService
from app.services.message_attachment_service import MessageAttachmentService
from app.services.session_resource_service import SessionResourceService


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
    session_id: Optional[str] = Form(None),
    resource_ids: Optional[str] = Form(None),  # comma-separated UUIDs
    top_k: int = 3,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat_session_service = ChatSessionService(db)

    # ----------------------------------------------------
    # 1️⃣ ENSURE SESSION EXISTS (voice-first fix)
    # ----------------------------------------------------
    if session_id in ("undefined", "null", "", None):
        session = chat_session_service.create_session(
            user_id=current_user.id,
            mode="learning",
            channel="voice",
            title="New Voice Chat",
        )
        parsed_session_id = session.id
    else:
        parsed_session_id = UUID(session_id)

    # ----------------------------------------------------
    # 2️⃣ SAVE AUDIO TEMP
    # ----------------------------------------------------
    temp_path = "temp.wav"
    with open(temp_path, "wb") as f:
        f.write(await audio.read())

    # ----------------------------------------------------
    # 3️⃣ UPLOAD AUDIO
    # ----------------------------------------------------
    audio_url = upload_audio_to_firebase(temp_path)

    # ----------------------------------------------------
    # 4️⃣ TRANSCRIBE
    # ----------------------------------------------------
    raw_text = VoiceService.transcribe_audio(temp_path)
    normalized, standard = VoiceService.standardize_southern_sinhala(raw_text)
    question_text = standard

    # ----------------------------------------------------
    # 5️⃣ SAVE USER MESSAGE (VOICE)
    # ----------------------------------------------------
    message_service = MessageService(db)

    user_message = message_service.create_user_message_with_validation(
        session_id=parsed_session_id,
        user_id=current_user.id,
        content=question_text,
        modality="voice",
        transcript=raw_text,
        audio_url=audio_url,
    )

    # ----------------------------------------------------
    # 6️⃣ ATTACH RESOURCES (IF ANY)
    # ----------------------------------------------------
    ids = []
    if resource_ids:
        ids = [UUID(rid) for rid in resource_ids.split(",")]

    attachment_service = MessageAttachmentService(db)
    session_resource_service = SessionResourceService(db)

    for rid in ids:
        attachment_service.attach_resource(
            message_id=user_message.id,
            resource_id=rid,
            attachment_type="resource",
        )
        session_resource_service.attach_resource_to_session(
            session_id=parsed_session_id,
            resource_id=rid,
        )

    # ----------------------------------------------------
    # 7️⃣ RESOLVE ALLOWED RESOURCES
    # ----------------------------------------------------
    allowed_resource_ids = get_allowed_resource_ids(
        db=db,
        session_id=parsed_session_id,
        message_id=user_message.id,
    )

    # ----------------------------------------------------
    # 8️⃣ RAG
    # ----------------------------------------------------
    top_chunks = retrieve_top_k(
        query=question_text,
        resource_ids=allowed_resource_ids,
        top_k=top_k,
    )

    prompt = VoiceQAService.build_prompt(question_text, top_chunks)
    answer = VoiceQAService.llm_generate(prompt)

    # ----------------------------------------------------
    # 9️⃣ SAVE ASSISTANT MESSAGE
    # ----------------------------------------------------
    message_service.create_assistant_message(
        session_id=parsed_session_id,
        content=answer,
    )

    # ----------------------------------------------------
    # 🔟 RESPONSE
    # ----------------------------------------------------
    return {
        "session_id": str(parsed_session_id),  # ✅ frontend needs this
        "question": question_text,
        "answer": answer,
        "retrieved_chunks": top_chunks,
    }
