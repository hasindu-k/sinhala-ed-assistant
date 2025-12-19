from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.auth import (
    SignUpRequest,
    SignInRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    RefreshTokenRequest,
    AuthTokensResponse,
    SignOutResponse,
)
from app.core.database import get_db
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.services.user_service import UserService

router = APIRouter()


@router.post("/signup", response_model=AuthTokensResponse)
def signup(payload: SignUpRequest, db: Session = Depends(get_db)):
    """Register a new user account."""
    service = UserService(db)
    existing = service.get_user_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = service.create_user(
        email=payload.email,
        full_name=payload.full_name,
        password=payload.password,
    )
    return AuthTokensResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/signin", response_model=AuthTokensResponse)
def signin(payload: SignInRequest, db: Session = Depends(get_db)):
    """Sign in with email and password."""
    service = UserService(db)
    user = service.get_user_by_email(payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return AuthTokensResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest):
    """Start password reset flow (stub)."""
    return {"detail": "Password reset instructions sent if the account exists."}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest):
    """Complete password reset (stub)."""
    return {"detail": "Password reset processed."}


@router.post("/refresh", response_model=AuthTokensResponse)
def refresh_token(payload: RefreshTokenRequest):
    """Issue a new access token using a refresh token."""
    try:
        data = decode_token(payload.refresh_token)
        if data.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id = data.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    return AuthTokensResponse(
        access_token=create_access_token(UUID(user_id)),
        refresh_token=create_refresh_token(UUID(user_id)),
    )


@router.post("/signout", response_model=SignOutResponse)
def signout():
    """Sign out (stateless stub)."""
    return SignOutResponse(success=True)
