from typing import Optional, Dict, Any
from uuid import UUID

from app.core.database import SessionLocal
from app.models.chat_message import ChatMessage


def save_chat_message(
    session_id: UUID,
    sender: str,
    message: Optional[str] = None,
    tokens_used: int = 0,
    audio_url: Optional[str] = None,
    image_url: Optional[str] = None,
    file_id: Optional[UUID] = None,
) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        cm = ChatMessage(
            session_id=session_id,
            sender=sender,
            message=message,
            tokens_used=tokens_used,
            audio_url=audio_url,
            image_url=image_url,
            file_id=file_id,
        )
        db.add(cm)
        db.commit()
        db.refresh(cm)
        return {
            "id": str(cm.id),
            "session_id": str(cm.session_id),
            "sender": cm.sender,
            "message": cm.message,
            "tokens_used": cm.tokens_used,
            "audio_url": cm.audio_url,
            "created_at": cm.created_at.isoformat() if cm.created_at else None,
        }
    finally:
        db.close()
