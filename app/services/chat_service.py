from typing import Optional, Dict, Any
from uuid import UUID

from app.core.database import SessionLocal
from app.shared.models.message import Message


def save_chat_message(
    session_id: UUID,
    role: str,
    content: Optional[str] = None,
    modality: str = "text",
    audio_url: Optional[str] = None,
    transcript: Optional[str] = None,
    audio_duration_sec: Optional[float] = None,
    model_name: Optional[str] = None,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
    grade_level: Optional[str] = None,
) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        msg = Message(
            session_id=session_id,
            role=role,
            content=content,
            modality=modality,
            audio_url=audio_url,
            transcript=transcript,
            audio_duration_sec=audio_duration_sec,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            grade_level=grade_level,
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return {
            "id": str(msg.id),
            "session_id": str(msg.session_id),
            "role": msg.role,
            "content": msg.content,
            "modality": msg.modality,
            "audio_url": msg.audio_url,
            "transcript": msg.transcript,
            "audio_duration_sec": float(msg.audio_duration_sec) if msg.audio_duration_sec else None,
            "model_name": msg.model_name,
            "prompt_tokens": msg.prompt_tokens,
            "completion_tokens": msg.completion_tokens,
            "total_tokens": msg.total_tokens,
            "grade_level": msg.grade_level,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        }
    finally:
        db.close()
