import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
import uuid
from app.schemas.message import (
    MessageCreate,
    MessageDetachRequest,
    MessageDetail,
    MessageResponse,
    MessageAttachRequest,
    MessageAttachmentResponse,
    MessageContextChunkResponse,
    MessageSafetyReportResponse,
    GenerateResponseRequest
)
from app.services.message_service import MessageService
from app.services.message_attachment_service import MessageAttachmentService
from app.services.message_context_service import MessageContextService
from app.services.message_safety_service import MessageSafetyService
from app.services.chat_session_service import ChatSessionService
from app.services.rag_service import RAGService
from app.core.database import get_db
from app.core.security import get_current_user
from app.shared.models.user import User
from app.shared.models.message import Message
from typing import List

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/sessions/{session_id}", response_model=MessageResponse)
def create_user_message(
    session_id: str,
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        chat_session_service = ChatSessionService(db)

        # 🔑 If frontend sends "undefined", CREATE SESSION PROPERLY
        if session_id in ("undefined", "null", "", None):
            session = chat_session_service.create_session(
                user_id=current_user.id,
                mode="learning",      # or infer later
                channel="text",
                title="New Chat",
            )
            parsed_session_id = session.id
        else:
            parsed_session_id = UUID(session_id)

        message_service = MessageService(db)

        message = message_service.create_user_message_with_validation(
            session_id=parsed_session_id,   # ✅ guaranteed to exist
            user_id=current_user.id,
            content=payload.content,
            modality=payload.modality,
            grade_level=payload.grade_level,
            audio_url=payload.audio_url,
            transcript=payload.transcript,
            audio_duration_sec=payload.audio_duration_sec,
        )

        return message

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create message", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to create message",
        )

@router.get("/{message_id}", response_model=MessageResponse)
def get_message(
    message_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a single message.
    
    Args:
        message_id: ID of the message to retrieve
        current_user: Authenticated user
        db: Database session
        
    Returns:
        MessageResponse with message details
        
    Raises:
        HTTPException 403: User doesn't own the session
        HTTPException 404: Message not found
        HTTPException 500: Database error
    """
    try:
        message_service = MessageService(db)
        message = message_service.get_message_with_ownership_check(message_id, current_user.id)
        logger.debug(f"Retrieved message {message_id} for user {current_user.id}")
        return message
        
    except ValueError as e:
        logger.warning(f"Message {message_id} not found for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"User {current_user.id} attempted unauthorized access to message {message_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error retrieving message {message_id} for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve message"
        )


@router.get("/{message_id}/details", response_model=MessageDetail)
def get_message_details(
    message_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a single message with all details (attachments, context, safety).
    
    Args:
        message_id: ID of the message
        current_user: Authenticated user
        db: Database session
        
    Returns:
        MessageDetail with full message information
        
    Raises:
        HTTPException 403: User doesn't own the session
        HTTPException 404: Message not found
        HTTPException 500: Database error
    """
    try:
        message_service = MessageService(db)
        details = message_service.get_message_details(message_id, current_user.id)
        logger.debug(f"Retrieved message details for {message_id} by user {current_user.id}")
        return details
        
    except ValueError as e:
        logger.warning(f"Message {message_id} not found for details request by user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"User {current_user.id} attempted unauthorized access to message details {message_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error retrieving message details {message_id} for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve message details"
        )


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(
    message_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a message.
    
    Args:
        message_id: ID of the message to delete
        current_user: Authenticated user
        db: Database session
        
    Raises:
        HTTPException 403: User doesn't own the session
        HTTPException 404: Message not found
        HTTPException 500: Database error
    """
    try:
        message_service = MessageService(db)
        message_service.delete_message(message_id, current_user.id)
        logger.info(f"Message {message_id} deleted by user {current_user.id}")
        
    except ValueError as e:
        logger.warning(f"Message {message_id} not found for deletion by user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"User {current_user.id} attempted unauthorized deletion of message {message_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting message {message_id} for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete message"
        )


@router.post("/{message_id}/attachments", response_model=List[MessageAttachmentResponse])
def attach_files_to_message(
    message_id: UUID,
    payload: MessageAttachRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Attach files/resources that are relevant only to this message.
    
    Args:
        message_id: ID of the message
        payload: Resource attachment data
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of MessageAttachmentResponse objects
        
    Raises:
        HTTPException 400: Invalid resource IDs
        HTTPException 403: User doesn't own the session
        HTTPException 404: Message not found
        HTTPException 500: Database error
    """
    try:
        message_service = MessageService(db)
        attachments = message_service.attach_resources_to_message(
            message_id=message_id,
            user_id=current_user.id,
            resource_ids=payload.resource_ids,
            display_name=payload.display_name,
            attachment_type=payload.attachment_type,
        )
        logger.info(f"Attached {len(attachments)} resources to message {message_id} by user {current_user.id}")
        return attachments
        
    except ValueError as e:
        logger.warning(f"Validation error attaching resources to message {message_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"User {current_user.id} attempted unauthorized attachment to message {message_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error attaching resources to message {message_id} for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to attach resources"
        )

# remove attachments
@router.delete("/{message_id}/attachments", status_code=status.HTTP_204_NO_CONTENT)
def detach_files_from_message(
    message_id: UUID,
    payload: MessageDetachRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Detach files/resources from this message.
    
    Args:
        message_id: ID of the message
        payload: Resource detachment data
        current_user: Authenticated user
        db: Database session
    Raises:
        HTTPException 400: Invalid resource IDs
        HTTPException 403: User doesn't own the session
        HTTPException 404: Message not found
        HTTPException 500: Database error
    """
    try:
        message_service = MessageService(db)
        message_service.detach_resources_from_message(
            message_id=message_id,
            user_id=current_user.id,
            resource_ids=payload.resource_ids,
        )
        logger.info(f"Detached resources from message {message_id} by user {current_user.id}")
        
    except ValueError as e:
        logger.warning(f"Validation error detaching resources from message {message_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"User {current_user.id} attempted unauthorized detachment from message {message_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error detaching resources from message {message_id} for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to detach resources"
        )

@router.post("/{message_id}/generate", response_model=MessageResponse)
def generate_ai_response(
    message_id: UUID,
    payload: GenerateResponseRequest = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate assistant response using RAG.
    
    Args:
        message_id: ID of the user message to respond to
        payload: Optional generation parameters
        current_user: Authenticated user
        db: Database session
        
    Returns:
        MessageResponse with generated assistant message
        
    Raises:
        HTTPException 400: Invalid parameters or message type
        HTTPException 403: User doesn't own the session
        HTTPException 404: Message not found
        HTTPException 500: Generation or database error
    """
    try:
        message_service = MessageService(db)
        # get resource IDs from message attachments if not provided get session level resources
        attachments = message_service.get_message_attachments(message_id, current_user.id)
        resource_ids = [att.resource_id for att in attachments]
        # if not resource_ids:
            # get session level resources

        assistant_message = message_service.generate_ai_response(
            message_id=message_id,
            user_id=current_user.id,
            resource_ids=resource_ids,
        )
        logger.info(f"AI response generated for message {message_id} by user {current_user.id}")
        return assistant_message
        
    except ValueError as e:
        logger.warning(f"Validation error generating response for message {message_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"User {current_user.id} attempted unauthorized response generation for message {message_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating response for message {message_id} for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate AI response"
        )


@router.get("/sessions/{session_id}", response_model=List[MessageResponse])
def get_message_history(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all messages for a session.
    
    Args:
        session_id: ID of the chat session
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of MessageResponse objects in chronological order
        
    Raises:
        HTTPException 403: User doesn't own the session
        HTTPException 404: Session not found
        HTTPException 500: Database error
    """
    try:
        session_service = ChatSessionService(db)
        session_service.get_session_with_ownership_check(session_id, current_user.id)
        
        message_service = MessageService(db)
        messages = message_service.list_session_messages(session_id)
        
        logger.debug(f"Retrieved {len(messages)} messages for session {session_id} by user {current_user.id}")
        return messages
        
    except ValueError as e:
        logger.warning(f"Session {session_id} not found for message history by user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"User {current_user.id} attempted unauthorized access to message history for session {session_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error retrieving message history for session {session_id} for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve message history"
        )


@router.get("/{message_id}/sources", response_model=List[MessageContextChunkResponse])
def get_message_sources(
    message_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get resource chunks used for this response.
    
    Args:
        message_id: ID of the assistant message
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of MessageContextChunkResponse objects
        
    Raises:
        HTTPException 403: User doesn't own the session
        HTTPException 404: Message not found
        HTTPException 500: Database error
    """
    try:
        message_service = MessageService(db)
        message_service.get_message_with_ownership_check(message_id, current_user.id)
        
        context_service = MessageContextService(db)
        sources = context_service.get_message_sources(message_id)
        
        logger.debug(f"Retrieved {len(sources)} sources for message {message_id} by user {current_user.id}")
        return sources
        
    except ValueError as e:
        logger.warning(f"Message {message_id} not found for sources request by user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"User {current_user.id} attempted unauthorized access to sources for message {message_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error retrieving sources for message {message_id} for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve message sources"
        )


@router.get("/{message_id}/safety", response_model=MessageSafetyReportResponse)
def get_message_safety_report(
    message_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get hallucination/safety report for an assistant message.
    
    Args:
        message_id: ID of the assistant message
        current_user: Authenticated user
        db: Database session
        
    Returns:
        MessageSafetyReportResponse with safety analysis
        
    Raises:
        HTTPException 403: User doesn't own the session
        HTTPException 404: Message or report not found
        HTTPException 500: Database error
    """
    try:
        message_service = MessageService(db)
        message_service.get_message_with_ownership_check(message_id, current_user.id)
        
        safety_service = MessageSafetyService(db)
        safety_report = safety_service.get_safety_report(message_id)
        
        if not safety_report:
            logger.warning(f"Safety report not found for message {message_id} by user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Safety report not found for this message"
            )
        
        logger.debug(f"Retrieved safety report for message {message_id} by user {current_user.id}")
        return safety_report
        
    except ValueError as e:
        logger.warning(f"Message {message_id} not found for safety report by user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"User {current_user.id} attempted unauthorized access to safety report for message {message_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving safety report for message {message_id} for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve safety report"
        )
