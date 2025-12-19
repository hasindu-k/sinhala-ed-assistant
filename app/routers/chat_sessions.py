from fastapi import APIRouter
from uuid import UUID
from app.schemas.chat import ChatSessionCreate

router = APIRouter()


@router.post("/sessions")
def create_chat_session(payload: ChatSessionCreate):
    """
    Create a new chat session (learning or evaluation).
    """
    pass


@router.get("/sessions")
def list_chat_sessions():
    """
    Get all chat sessions for the logged-in user.
    """
    pass


@router.get("/sessions/{session_id}")
def get_chat_session(session_id: UUID):
    """
    Get a single chat session with metadata.
    """
    pass


@router.post("/sessions/{session_id}/resources")
def attach_resources_to_session(session_id: UUID, resource_ids: list[UUID]):
    """
    Attach resources permanently to a session.
    """
    pass
