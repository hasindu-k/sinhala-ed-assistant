from fastapi import APIRouter, Depends, HTTPException, Query, status
from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session

from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
)
from app.core.database import get_db
from app.core.security import get_current_user
from app.services.user_service import UserService

router = APIRouter()


@router.get("/me", response_model=UserResponse)
def get_me(current_user=Depends(get_current_user)):
    """Get the currently authenticated user's profile."""
    return current_user


@router.post("/", response_model=UserResponse)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    """Create a new user (admin/public)."""
    service = UserService(db)
    existing = service.get_user_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    return service.create_user(
        email=payload.email,
        full_name=payload.full_name,
        password=payload.password,
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: UUID, db: Session = Depends(get_db)):
    """Get a user by ID."""
    service = UserService(db)
    user = service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("/by-email", response_model=UserResponse)
def get_user_by_email(email: str = Query(..., description="User email"), db: Session = Depends(get_db)):
    """Get a user by email."""
    service = UserService(db)
    user = service.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: UUID, payload: UserUpdate, db: Session = Depends(get_db)):
    """Update a user's profile."""
    service = UserService(db)
    user = service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.email is not None:
        # Optional: check for duplicates
        existing = service.get_user_by_email(payload.email)
        if existing and existing.id != user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use")
        user.email = payload.email
    return service.update_user(
        user,
        full_name=payload.full_name,
        email=payload.email,
        password=payload.password,
    )
