from fastapi import APIRouter
from uuid import UUID
from app.schemas.message import MessageCreate

router = APIRouter()


@router.post("/sessions/{session_id}")
def create_user_message(session_id: UUID, payload: MessageCreate):
    """
    Create a user message (text or voice).
    """
    pass


@router.post("/{message_id}/attachments")
def attach_files_to_message(message_id: UUID, resource_ids: list[UUID]):
    """
    Attach files that are relevant only to this message.
    """
    pass


@router.post("/{message_id}/generate")
def generate_ai_response(message_id: UUID):
    """
    Generate assistant response using RAG.
    """
    pass


@router.get("/sessions/{session_id}")
def get_message_history(session_id: UUID):
    """
    Get all messages for a session.
    """
    pass


@router.get("/{message_id}/sources")
def get_message_sources(message_id: UUID):
    """
    Get resource chunks used for this response.
    """
    pass


@router.get("/{message_id}/safety")
def get_message_safety_report(message_id: UUID):
    """
    Get hallucination/safety report for an assistant message.
    """
    pass
