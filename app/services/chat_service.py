import uuid
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.shared.models import chat_message


def save_chat_message(
    *,
    session_id,
    role: str,
    modality: str,
    content: Optional[str] = None,
    transcript: Optional[str] = None,
    audio_url: Optional[str] = None,
    grade_level: Optional[str] = None,
    model_name: Optional[str] = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
):
    """
    Save a message into `messages` table.

    Notes:
    - content   → what appears in chat UI
    - transcript → raw ASR output (voice only)
    - modality  → 'voice' | 'text' | 'image' | 'file'
    """

    db: Session = next(get_db())

    total_tokens = prompt_tokens + completion_tokens

    msg = chat_message(
        id=uuid.uuid4(),
        session_id=session_id,
        role=role,
        modality=modality,
        content=content,
        transcript=transcript,
        audio_url=audio_url,
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
