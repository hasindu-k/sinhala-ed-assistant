# app/services/usage_service.py

import logging
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from app.shared.models.user import User
from app.shared.models.chat_session import ChatSession
from app.shared.models.evaluation_session import EvaluationSession
from app.core.config import settings

logger = logging.getLogger(__name__)

class UsageService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_tier_limit(self, tier: str) -> int:
        """Get the evaluation limit for a given tier."""
        tier = tier.lower()
        if tier == "basic":
            return settings.EVALUATION_LIMIT_BASIC
        elif tier == "classroom":
            return settings.EVALUATION_LIMIT_CLASSROOM
        elif tier == "institution":
            return settings.EVALUATION_LIMIT_INSTITUTION
        else:
            return settings.EVALUATION_LIMIT_NORMAL

    def check_evaluation_limit(self, user_id: UUID):
        """
        Check if a user has exceeded their evaluation limit within the last 12 hours.
        Raises HTTPException if the limit is exceeded.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        limit = self.get_user_tier_limit(user.tier)
        
        # Institution package has unlimited evaluations
        if limit == -1:
            return True

        # Calculate the time threshold (12 hours ago)
        duration_hours = settings.EVALUATION_LIMIT_DURATION_HOURS
        threshold_time = datetime.now() - timedelta(hours=duration_hours)

        # Count evaluation sessions created by this user in the last threshold_time
        # EvaluationSession -> ChatSession -> User
        count = (
            self.db.query(func.count(EvaluationSession.id))
            .join(ChatSession, EvaluationSession.session_id == ChatSession.id)
            .filter(ChatSession.user_id == user_id)
            .filter(EvaluationSession.created_at >= threshold_time)
            .scalar()
        )

        if count >= limit:
            logger.warning(f"User {user_id} (Tier: {user.tier}) reached evaluation limit: {count}/{limit}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Evaluation limit reached for your {user.tier} package ({limit} evaluations per {duration_hours} hours). "
                       f"Please try again later or upgrade your package."
            )

        return True
