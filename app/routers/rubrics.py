# app/routers/rubrics.py

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.schemas.rubric import (
    RubricCreate,
    RubricUpdate,
    RubricResponse,
    RubricDetail,
    RubricCriterionCreate,
    RubricCriterionUpdate,
    RubricCriterionResponse,
)
from app.services.evaluation.rubric_service import RubricService
from app.services.evaluation.user_context_service import UserContextService
from app.core.database import get_db
from app.core.security import get_current_user
from app.shared.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/{rubric_id}/activate", response_model=RubricResponse)
def activate_rubric(
    rubric_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Set a rubric as the active rubric for the user.
    """
    service = RubricService(db)
    rubric = service.get_rubric(rubric_id)
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")
        
    context_service = UserContextService(db)
    context_service.update_rubric(current_user.id, rubric_id)
    
    return rubric



@router.get("/", response_model=List[RubricResponse])
def list_rubrics(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    List system and user-created rubrics.
    """
    service = RubricService(db)
    return service.get_rubrics_by_user(current_user.id)


@router.post("/", response_model=RubricResponse)
def create_rubric(
    payload: RubricCreate, 
    chat_session_id: Optional[UUID] = Query(None, description="Optional chat session ID to attach the rubric to"),
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    Create a custom rubric.
    """
    service = RubricService(db)
    try:
        rubric = service.create_rubric(
            current_user.id,
            payload.name,
            payload.description,
            payload.rubric_type,
            payload.criteria,
        )
        
        if chat_session_id:
            from app.services.chat_session_service import ChatSessionService
            chat_service = ChatSessionService(db)
            # Verify ownership and existence
            session = chat_service.get_session_with_ownership_check(chat_session_id, current_user.id)
            
            # Update session with rubric_id
            # We can use a repository method or service method if available, or direct update here for now
            # Ideally, ChatSessionService should have update_session method
            chat_service.update_session(chat_session_id, user_id=current_user.id, rubric_id=rubric.id)
            
            # Also update user context if it's an evaluation session
            if session.mode == "evaluation":
                context_service = UserContextService(db)
                context_service.update_rubric(current_user.id, rubric.id)
                
        return rubric
    except Exception as exc:
        logger.error(f"Failed to create rubric for user {current_user.id}: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create rubric")


@router.post("/system", response_model=RubricResponse)
def create_system_rubric(payload: RubricCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Create a system rubric (admin-only): created_by=NULL, rubric_type='system'.
    """
    service = RubricService(db)
    # Basic admin check; adjust to your auth/roles model
    is_admin = bool(getattr(current_user, "is_admin", True) or getattr(current_user, "role", None) == "admin")
    if not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    try:
        return service.create_system_rubric(
            name=payload.name,
            description=payload.description,
            criteria=payload.criteria,
        )
    except Exception as exc:
        logger.error(f"Failed to create system rubric: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create system rubric")


@router.get("/{rubric_id}", response_model=RubricDetail)
def get_rubric(rubric_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get rubric with criteria.
    """
    service = RubricService(db)
    try:
        detail = service.get_rubric_with_criteria(rubric_id, current_user.id)
        if not detail:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rubric not found")
        return detail
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.put("/{rubric_id}", response_model=RubricResponse)
def update_rubric(rubric_id: UUID, payload: RubricUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Update rubric metadata.
    """
    service = RubricService(db)
    try:
        updated = service.update_rubric(
            rubric_id,
            current_user.id,
            payload.name,
            payload.description,
            payload.rubric_type,
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rubric not found")
        return updated
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/{rubric_id}")
def delete_rubric(rubric_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Delete a rubric.
    """
    service = RubricService(db)
    try:
        success = service.delete_rubric(rubric_id, current_user.id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rubric not found")
        return {"detail": "Rubric deleted"}
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/{rubric_id}/criteria", response_model=RubricCriterionResponse)
def add_criterion(rubric_id: UUID, payload: RubricCriterionCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Add a criterion to a rubric.
    """
    service = RubricService(db)
    try:
        return service.create_rubric_criterion(
            rubric_id=rubric_id,
            user_id=current_user.id,
            criterion=payload.criterion,
            weight_percentage=payload.weight_percentage,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.put("/{rubric_id}/criteria/{criterion_id}", response_model=RubricCriterionResponse)
def update_criterion(rubric_id: UUID, criterion_id: UUID, payload: RubricCriterionUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Update a rubric criterion.
    """
    service = RubricService(db)
    try:
        updated = service.update_rubric_criterion(
            rubric_id=rubric_id,
            criterion_id=criterion_id,
            user_id=current_user.id,
            criterion=payload.criterion,
            weight_percentage=payload.weight_percentage,
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Criterion not found")
        return updated
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/{rubric_id}/criteria/{criterion_id}")
def delete_criterion(rubric_id: UUID, criterion_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Delete a rubric criterion.
    """
    service = RubricService(db)
    try:
        success = service.delete_rubric_criterion(rubric_id, criterion_id, current_user.id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Criterion not found")
        return {"detail": "Criterion deleted"}
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
