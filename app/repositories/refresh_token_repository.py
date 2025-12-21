from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.shared.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    """Data access for RefreshToken model."""

    def __init__(self, db: Session):
        self.db = db

    def create_token(self, user_id: UUID, token_jti: str, expires_at: datetime) -> RefreshToken:
        """Store a new refresh token."""
        token = RefreshToken(user_id=user_id, token_jti=token_jti, expires_at=expires_at)
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token

    def get_token(self, token_jti: str) -> Optional[RefreshToken]:
        """Retrieve token by JTI."""
        return self.db.query(RefreshToken).filter(RefreshToken.token_jti == token_jti).first()

    def is_token_valid(self, token_jti: str) -> bool:
        """Check if token is active and not expired/revoked."""
        token = self.get_token(token_jti)
        if not token:
            return False
        # Token is valid if not revoked and not expired
        return (
            token.revoked_at is None
            and token.expires_at > datetime.now(timezone.utc)
        )

    def revoke_token(self, token_jti: str) -> bool:
        """Mark token as revoked."""
        token = self.get_token(token_jti)
        if not token:
            return False
        token.revoked_at = datetime.now(timezone.utc)
        self.db.add(token)
        self.db.commit()
        return True

    def revoke_all_user_tokens(self, user_id: UUID) -> int:
        """Revoke all active tokens for a user."""
        count = self.db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None)
        ).update({RefreshToken.revoked_at: datetime.now(timezone.utc)})
        self.db.commit()
        return count
