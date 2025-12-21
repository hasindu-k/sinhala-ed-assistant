from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.shared.models.password_reset_token import PasswordResetToken


class PasswordResetTokenRepository:
    """Data access for PasswordResetToken model."""

    def __init__(self, db: Session):
        self.db = db

    def create_token(self, user_id: UUID, token_jti: str, expires_at: datetime) -> PasswordResetToken:
        """Store a new password reset token."""
        token = PasswordResetToken(user_id=user_id, token_jti=token_jti, expires_at=expires_at)
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token

    def get_token(self, token_jti: str) -> Optional[PasswordResetToken]:
        """Retrieve token by JTI."""
        return self.db.query(PasswordResetToken).filter(PasswordResetToken.token_jti == token_jti).first()

    def is_token_valid(self, token_jti: str) -> bool:
        """Check if token is active, not expired, not used, and not revoked."""
        token = self.get_token(token_jti)
        if not token:
            return False
        # Token is valid if not used, not revoked, and not expired
        return (
            token.used_at is None
            and token.revoked_at is None
            and token.expires_at > datetime.now(timezone.utc)
        )

    def mark_token_as_used(self, token_jti: str) -> bool:
        """Mark token as used after successful password reset."""
        token = self.get_token(token_jti)
        if not token:
            return False
        token.used_at = datetime.now(timezone.utc)
        self.db.add(token)
        self.db.commit()
        return True

    def revoke_all_user_tokens(self, user_id: UUID) -> int:
        """Revoke all active reset tokens for a user (when new reset is requested)."""
        count = self.db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.revoked_at.is_(None)
        ).update({PasswordResetToken.revoked_at: datetime.now(timezone.utc)})
        self.db.commit()
        return count
