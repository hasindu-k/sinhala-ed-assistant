# app/routers/chat_sessions.py

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from app.schemas.chat import ChatSessionCreate, ChatSessionUpdate, ChatSessionResponse, SessionResourceAttach
from app.schemas.resource import ResourceFileResponse
from app.services.chat_session_service import ChatSessionService
from app.services.session_resource_service import SessionResourceService
from app.core.database import get_db
from app.core.security import get_current_user
from app.shared.models.user import User
from typing import List

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/sessions", response_model=ChatSessionResponse)
def create_chat_session(
    payload: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new chat session (learning or evaluation).
    
    Args:
        payload: Chat session creation data
        current_user: Authenticated user
        db: Database session
        
    Returns:
        ChatSessionResponse with created session details
        
    Raises:
        HTTPException 400: Invalid input parameters
        HTTPException 500: Database or internal error
    """
    try:
        service = ChatSessionService(db)
        session = service.create_session(
            user_id=current_user.id,
            mode=payload.mode,
            channel=payload.channel,
            title=payload.title,
            description=payload.description,
            grade=payload.grade,
            subject=payload.subject,
            rubric_id=payload.rubric_id,
        )
        logger.info(f"Chat session created: {session.id} for user {current_user.id}")
        return session
        
    except ValueError as e:
        logger.warning(f"Validation error creating chat session: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating chat session for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create chat session"
        )


@router.get("/sessions", response_model=List[ChatSessionResponse])
def list_chat_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all chat sessions for the logged-in user.
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of ChatSessionResponse objects
        
    Raises:
        HTTPException 500: Database error
    """
    try:
        service = ChatSessionService(db)
        sessions = service.list_user_sessions(current_user.id)
        logger.debug(f"Retrieved {len(sessions)} sessions for user {current_user.id}")
        return sessions
        
    except Exception as e:
        logger.error(f"Error retrieving chat sessions for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat sessions"
        )


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
def get_chat_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a single chat session with metadata.
    
    Args:
        session_id: ID of the session to retrieve
        current_user: Authenticated user
        db: Database session
        
    Returns:
        ChatSessionResponse with session details
        
    Raises:
        HTTPException 403: User doesn't own the session
        HTTPException 404: Session not found
        HTTPException 500: Database error
    """
    try:
        service = ChatSessionService(db)
        session = service.get_session_with_ownership_check(session_id, current_user.id)
        logger.debug(f"Retrieved session {session_id} for user {current_user.id}")
        return session
        
    except PermissionError as e:
        logger.warning(f"User {current_user.id} attempted unauthorized access to session {session_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        logger.warning(f"Session {session_id} not found for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error retrieving session {session_id} for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat session"
        )


@router.put("/sessions/{session_id}", response_model=ChatSessionResponse)
def update_chat_session(
    session_id: UUID,
    payload: ChatSessionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update chat session metadata.
    
    Args:
        session_id: ID of the session to update
        payload: Session update data
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Updated ChatSessionResponse
        
    Raises:
        HTTPException 403: User doesn't own the session
        HTTPException 404: Session not found
        HTTPException 500: Database or internal error
    """
    try:
        service = ChatSessionService(db)
        session = service.update_session(
            session_id=session_id,
            user_id=current_user.id,
            title=payload.title,
            description=payload.description,
            grade=payload.grade,
            subject=payload.subject,
            rubric_id=payload.rubric_id,
        )
        logger.info(f"Chat session {session_id} updated by user {current_user.id}")
        return session
        
    except PermissionError as e:
        logger.warning(f"User {current_user.id} attempted unauthorized update to session {session_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        logger.warning(f"Session {session_id} not found for update by user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating session {session_id} for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update chat session"
        )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a chat session.
    
    Args:
        session_id: ID of the session to delete
        current_user: Authenticated user
        db: Database session
        
    Raises:
        HTTPException 403: User doesn't own the session
        HTTPException 404: Session not found
        HTTPException 500: Database or internal error
    """
    try:
        service = ChatSessionService(db)
        session_resources_service = SessionResourceService(db)
        session_resources_service.detach_all_resources(session_id)
        service.delete_session(session_id, current_user.id)
        logger.info(f"Chat session {session_id} deleted by user {current_user.id}")
        
    except PermissionError as e:
        logger.warning(f"User {current_user.id} attempted unauthorized deletion of session {session_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        logger.warning(f"Session {session_id} not found for deletion by user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting session {session_id} for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete chat session"
        )


@router.post("/sessions/{session_id}/attach-resource", status_code=status.HTTP_200_OK)
def attach_resource_to_session(
    session_id: UUID,
    payload: SessionResourceAttach,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Attach a resource (syllabus or question_paper) to a session.
    
    Args:
        session_id: ID of the session
        payload: Resource attachment data (resource_id, role)
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Confirmation message
    """
    try:
        service = ChatSessionService(db)
        result = service.attach_resource(
            session_id=session_id, 
            user_id=current_user.id, 
            resource_id=payload.resource_id, 
            role=payload.role
        )
        logger.info(f"Resource {payload.resource_id} attached as {payload.role} to session {session_id} by user {current_user.id}")
        return result
        
    except ValueError as e:
        logger.warning(f"Validation error attaching resource to session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"User {current_user.id} attempted unauthorized resource attachment to session {session_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error attaching resource to session {session_id} for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to attach resource to session"
        )


@router.get("/sessions/{session_id}/resources", response_model=List[ResourceFileResponse])
def get_session_resources(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all resources attached to a specific chat session.
    """
    try:
        # Verify session exists and belongs to user
        chat_service = ChatSessionService(db)
        session = chat_service.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        # Check ownership
        if hasattr(session, 'user_id') and session.user_id != current_user.id:
             raise HTTPException(status_code=403, detail="Not authorized to access this session")

        service = SessionResourceService(db)
        resources = service.get_resources_by_session_id(session_id)
        return resources
    except HTTPException:
        raise


@router.delete("/sessions/{session_id}/rubric", status_code=status.HTTP_200_OK)
def detach_rubric_from_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Detach the rubric from a chat session (does not delete the rubric)."""
    try:
        chat_service = ChatSessionService(db)
        session = chat_service.get_session_with_ownership_check(session_id, current_user.id)
        session.rubric_id = None
        db.commit()
        return {"detail": "Rubric detached"}
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(
            f"Error detaching rubric from session {session_id} for user {current_user.id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to detach rubric",
        )


@router.delete("/sessions/{session_id}/resources/{role}", status_code=status.HTTP_200_OK)
def detach_resource_from_session(
    session_id: UUID,
    role: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Detach a role-based resource (syllabus/question_paper) from a chat session (does not delete the resource)."""
    if role not in {"syllabus", "question_paper", "answer_script"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be 'syllabus', 'question_paper', or 'answer_script'",
        )

    try:
        chat_service = ChatSessionService(db)
        chat_service.get_session_with_ownership_check(session_id, current_user.id)

        session_resources_service = SessionResourceService(db)
        deleted = session_resources_service.detach_resources_by_label(session_id, role)
        return {"detail": f"{role} detached", "detached_count": deleted}
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(
            f"Error detaching {role} from session {session_id} for user {current_user.id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to detach resource from session",
        )


@router.delete("/sessions/{session_id}/answer-sheets/{resource_id}", status_code=status.HTTP_200_OK)
def detach_answer_sheet_from_session(
    session_id: UUID,
    resource_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Detach a single answer sheet (label 'answer_script') from a chat session (does not delete the resource)."""
    try:
        chat_service = ChatSessionService(db)
        chat_service.get_session_with_ownership_check(session_id, current_user.id)

        session_resources_service = SessionResourceService(db)
        deleted = session_resources_service.detach_resource(
            session_id=session_id,
            resource_id=resource_id,
            label="answer_script",
        )

        if deleted == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Answer sheet not attached to this session",
            )

        return {"detail": "Answer sheet detached", "detached_count": deleted}
    except HTTPException:
        raise
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(
            f"Error detaching answer sheet {resource_id} from session {session_id} for user {current_user.id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to detach answer sheet",
        )
    except Exception as e:
        logger.error(f"Error fetching resources for session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch session resources"
        )

