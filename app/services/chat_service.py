import uuid
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.shared.models.message import Message


def save_chat_message(
    *,
    session_id: UUID,
    role: str,
    modality: str,
    content: Optional[str] = None,
    transcript: Optional[str] = None,
    audio_url: Optional[str] = None,
    audio_duration_sec: Optional[float] = None,
    grade_level: Optional[str] = None,
    model_name: Optional[str] = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
) -> UUID:
    """
    Save a message into `messages` table.

    Rules:
    - content     → what appears in chat UI
    - transcript  → raw ASR output (voice only)
    - modality    → 'voice' | 'text' | 'image' | 'file'
    """

    db: Session = SessionLocal()

    try:
        total_tokens = prompt_tokens + completion_tokens

        msg = Message(
            id=uuid.uuid4(),
            session_id=session_id,
            role=role,
            modality=modality,
            content=content,
            transcript=transcript,
            audio_url=audio_url,
            audio_duration_sec=audio_duration_sec,
            grade_level=grade_level,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

        db.add(msg)
        db.commit()
        db.refresh(msg)

        return msg.id

    finally:
        db.close()
        
