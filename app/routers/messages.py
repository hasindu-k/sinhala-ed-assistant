from fastapi import APIRouter
from uuid import UUID
from app.schemas.message import (
    MessageCreate,
    MessageDetail,
    MessageResponse,
    MessageDetail,
    MessageAttachRequest,
    MessageAttachmentResponse,
    MessageContextChunkResponse,
    MessageSafetyReportResponse,
    GenerateResponseRequest
)
from typing import List

router = APIRouter()


@router.post("/sessions/{session_id}", response_model=MessageResponse)
def create_user_message(session_id: UUID, payload: MessageCreate):
    """
    Create a user message (text or voice).
    """
    pass


@router.get("/{message_id}", response_model=MessageResponse)
def get_message(message_id: UUID):
    """
    Get a single message.
    """
    pass


@router.get("/{message_id}/details", response_model=MessageDetail)
def get_message_details(message_id: UUID):
    """
    Get a single message with all details.
    """
    pass


@router.delete("/{message_id}")
def delete_message(message_id: UUID):
    """
    Delete a message.
    """
    pass


@router.post("/{message_id}/attachments", response_model=List[MessageAttachmentResponse])
def attach_files_to_message(message_id: UUID, payload: MessageAttachRequest):
    """
    Attach files that are relevant only to this message.
    """
    pass


@router.post("/{message_id}/generate", response_model=MessageResponse)
def generate_ai_response(message_id: UUID, payload: GenerateResponseRequest = None):
    """
    Generate assistant response using RAG.
    """
    pass


@router.get("/sessions/{session_id}", response_model=List[MessageResponse])
def get_message_history(session_id: UUID):
    """
    Get all messages for a session.
    """
    pass


@router.get("/{message_id}/sources", response_model=List[MessageContextChunkResponse])
def get_message_sources(message_id: UUID):
    """
    Get resource chunks used for this response.
    """
    pass


@router.get("/{message_id}/safety", response_model=MessageSafetyReportResponse)
def get_message_safety_report(message_id: UUID):
    """
    Get hallucination/safety report for an assistant message.
    """
    pass
