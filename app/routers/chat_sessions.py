from fastapi import APIRouter
from uuid import UUID
from app.schemas.chat import ChatSessionCreate, ChatSessionUpdate, ChatSessionResponse, SessionResourceAttach
from typing import List

router = APIRouter()


@router.post("/sessions", response_model=ChatSessionResponse)
def create_chat_session(payload: ChatSessionCreate):
    """
    Create a new chat session (learning or evaluation).
    """
    pass


@router.get("/sessions", response_model=List[ChatSessionResponse])
def list_chat_sessions():
    """
    Get all chat sessions for the logged-in user.
    """
    pass


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
def get_chat_session(session_id: UUID):
    """
    Get a single chat session with metadata.
    """
    pass


@router.put("/sessions/{session_id}", response_model=ChatSessionResponse)
def update_chat_session(session_id: UUID, payload: ChatSessionUpdate):
    """
    Update chat session metadata.
    """
    pass


@router.delete("/sessions/{session_id}")
def delete_chat_session(session_id: UUID):
    """
    Delete a chat session.
    """
    pass


@router.post("/sessions/{session_id}/resources")
def attach_resources_to_session(session_id: UUID, payload: SessionResourceAttach):
    """
    Attach resources permanently to a session.
    """
    pass
