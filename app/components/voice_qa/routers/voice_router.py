# app/components/voice_qa/routers/voice_router.py

from fastapi import APIRouter, Query, UploadFile, File, Form
from uuid import UUID
from jiwer import wer

from typing import Optional
from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
import subprocess
import os

from app.services.safety_summary_service import SafetySummaryService
from app.components.voice_qa.services.hybrid_retrieval import retrieve_top_k
from app.components.voice_qa.services.whisper_service import (
    VoiceService,
    VoiceQAService,
)
import logging

from app.utils.sinhala_safety_engine import (
    concept_map_check,
    detect_misconceptions,
    attach_evidence,
)
from app.services.safety_summary_service import SafetySummaryService
from app.services.message_safety_service import MessageSafetyService
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

logger = logging.getLogger(__name__)

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

@router.post("/evaluate-asr")
async def evaluate_asr(
    audio: UploadFile = File(...),
    reference_text: str = Form(...)
):
    temp_path = "temp.wav"

    with open(temp_path, "wb") as f:
        f.write(await audio.read())

    result = VoiceService.evaluate_audio(temp_path, reference_text)

    os.remove(temp_path)

    return result
# The heavier pipeline helpers live in `VoiceQAService` (in whisper_service.py).


@router.post("/qa")
async def qa_from_voice(
    audio: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    resource_ids: Optional[str] = Form(None),  # comma-separated UUIDs
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    
    logger.info("Entered qa_from_voice function")  # This will confirm if the function is being hit.
    
    logger.info(f"Received session_id: {session_id}, resource_ids: {resource_ids}, user_id: {current_user.id}")
    
    chat_session_service = ChatSessionService(db)
    message_service = MessageService(db)

    # ----------------------------------------------------
    # 1️⃣ ENSURE SESSION EXISTS
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
    # 4️⃣ TRANSCRIBE + NORMALIZE
    # ----------------------------------------------------
    raw_text = VoiceService.transcribe_audio(temp_path)
    _, standard = VoiceService.standardize_southern_sinhala(raw_text)
    question_text = standard

    # ----------------------------------------------------
    # 5️⃣ SAVE USER MESSAGE (VOICE)
    # ----------------------------------------------------
    user_message = message_service.create_user_message_with_validation(
        session_id=parsed_session_id,
        user_id=current_user.id,
        content=question_text,
        modality="voice",
        transcript=raw_text,
        audio_url=audio_url,
    )

    # ----------------------------------------------------
    # 6️⃣ ATTACH RESOURCES (IF PROVIDED)
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

    logger.info(f"Message ID: {user_message.id}")
    logger.info(f"Session ID: {parsed_session_id}")
    # ----------------------------------------------------
    # 7️⃣ RESOLVE ALLOWED RESOURCES
    # ----------------------------------------------------
    allowed_resource_ids = get_allowed_resource_ids(
        db=db,
        session_id=parsed_session_id,
        message_id=user_message.id,
    )
    
    print(f"Allowed Resource IDs: {allowed_resource_ids}")

    # ----------------------------------------------------
    # 8️⃣ GENERATE ANSWER (DELEGATE TO TEXT RAG)
    # ----------------------------------------------------
    assistant_msg = message_service.generate_ai_response(
        message_id=user_message.id,
        user_id=current_user.id,
        resource_ids=allowed_resource_ids,
    )

    logger.info(
        "Voice QA completed | session=%s | user=%s | assistant_msg=%s",
        parsed_session_id,
        current_user.id,
        assistant_msg.id,
    )

    # ----------------------------------------------------
    # 🔟 RESPONSE
    # ----------------------------------------------------
    summary_service = SafetySummaryService(db)
    summary = summary_service.build_summary(assistant_msg.id)
    
    return {
    "session_id": str(parsed_session_id),
    "question": question_text,
    "answer": assistant_msg.content,
    "assistant_message_id": str(assistant_msg.id),
    "safety_summary": {
        "overall_severity": summary.get("overall_severity"),
        "confidence_score": summary.get("confidence_score"),
        "reliability": summary.get("reliability"),
    } if summary else None,
    }
    
    
@router.post("/qa-from-text")
async def qa_from_text(
    text: str = Form(...),  # Get transcribed text from frontend
    session_id: Optional[str] = Form(None),
    resource_ids: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info("Entered qa_from_text function")
    logger.info(f"Received text: {text[:50]}..., session_id: {session_id}, user_id: {current_user.id}")
    
    chat_session_service = ChatSessionService(db)
    message_service = MessageService(db)

    # ----------------------------------------------------
    # 1️⃣ ENSURE SESSION EXISTS
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
    # 2️⃣ SAVE USER MESSAGE (NO AUDIO UPLOAD NEEDED)
    # ----------------------------------------------------
    user_message = message_service.create_user_message_with_validation(
        session_id=parsed_session_id,
        user_id=current_user.id,
        content=text,  # Use the transcribed text directly
        modality="voice",
        transcript=text,  # Same as content since it's already transcribed
        audio_url=None,  # No audio file to upload
    )

    # ----------------------------------------------------
    # 3️⃣ ATTACH RESOURCES (IF PROVIDED)
    # ----------------------------------------------------
    ids = []
    if resource_ids:
        ids = [UUID(rid.strip()) for rid in resource_ids.split(",") if rid.strip()]

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

    logger.info(f"Message ID: {user_message.id}")
    logger.info(f"Session ID: {parsed_session_id}")
    
    # ----------------------------------------------------
    # 4️⃣ RESOLVE ALLOWED RESOURCES
    # ----------------------------------------------------
    allowed_resource_ids = get_allowed_resource_ids(
        db=db,
        session_id=parsed_session_id,
        message_id=user_message.id,
    )
    
    logger.info(f"Allowed Resource IDs: {allowed_resource_ids}")

    # ----------------------------------------------------
    # 5️⃣ GENERATE ANSWER (DELEGATE TO TEXT RAG)
    # ----------------------------------------------------
    assistant_msg = message_service.generate_ai_response(
        message_id=user_message.id,
        user_id=current_user.id,
        resource_ids=allowed_resource_ids,
    )

    logger.info(
        "Voice QA from text completed | session=%s | user=%s | assistant_msg=%s",
        parsed_session_id,
        current_user.id,
        assistant_msg.id,
    )

    # ----------------------------------------------------
    # 6️⃣ SAFETY SUMMARY
    # ----------------------------------------------------
    summary_service = SafetySummaryService(db)
    summary = summary_service.build_summary(assistant_msg.id)
    
    return {
        "session_id": str(parsed_session_id),
        "question": text,
        "answer": assistant_msg.content,
        "assistant_message_id": str(assistant_msg.id),
        "safety_summary": {
            "overall_severity": summary.get("overall_severity"),
            "confidence_score": summary.get("confidence_score"),
            "reliability": summary.get("reliability"),
        } if summary else None,
    }