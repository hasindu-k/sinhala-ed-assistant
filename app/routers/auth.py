from uuid import UUID
from datetime import datetime, timezone

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
    create_password_reset_token,
    get_current_user,
)
from app.services.user_service import UserService
from app.repositories.refresh_token_repository import RefreshTokenRepository

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
    
    # Issue tokens and store refresh token
    access_token = create_access_token(user.id)
    refresh_token, jti, expires_at = create_refresh_token(user.id)
    
    token_repo = RefreshTokenRepository(db)
    token_repo.create_token(user.id, jti, expires_at)
    
    return AuthTokensResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/signin", response_model=AuthTokensResponse)
def signin(payload: SignInRequest, db: Session = Depends(get_db)):
    """Sign in with email and password."""
    service = UserService(db)
    user = service.get_user_by_email(payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    # Update last login timestamp
    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    db.commit()

    # Issue tokens and store refresh token
    access_token = create_access_token(user.id)
    refresh_token, jti, expires_at = create_refresh_token(user.id)
    
    token_repo = RefreshTokenRepository(db)
    token_repo.create_token(user.id, jti, expires_at)

    return AuthTokensResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Start password reset flow: generate a short-lived reset token.

    In production, you'd email this token to the user. Here, we return it
    conditionally for development/testing.
    """
    service = UserService(db)
    user = service.get_user_by_email(payload.email)

    # Always return a generic message; include token only if the account exists.
    response = {"detail": "Password reset instructions sent if the account exists."}
    if user:
        response["reset_token"] = create_password_reset_token(user.id)
    return response


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Complete password reset: verify token and update password."""
    # Validate token
    try:
        data = decode_token(payload.token)
        if data.get("type") != "reset":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id = data.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    service = UserService(db)
    user = service.get_user(UUID(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    service.update_user(user, password=payload.new_password)
    return {"detail": "Password reset processed."}


@router.post("/refresh", response_model=AuthTokensResponse)
def refresh_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Issue a new access token using a refresh token."""
    try:
        data = decode_token(payload.refresh_token)
        if data.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id = data.get("sub")
        jti = data.get("jti")
        if not user_id or not jti:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    # Verify token is still active in DB
    token_repo = RefreshTokenRepository(db)
    if not token_repo.is_token_valid(jti):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked or expired")

    # Issue new tokens
    access_token = create_access_token(UUID(user_id))
    refresh_token_str, new_jti, expires_at = create_refresh_token(UUID(user_id))
    
    # Store new refresh token
    token_repo.create_token(UUID(user_id), new_jti, expires_at)

    return AuthTokensResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
    )


@router.post("/signout", response_model=SignOutResponse)
def signout(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Sign out: revoke all refresh tokens for the user."""
    token_repo = RefreshTokenRepository(db)
    token_repo.revoke_all_user_tokens(current_user.id)
    return SignOutResponse(success=True)
