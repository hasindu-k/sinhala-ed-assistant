# app/repositories/user_repository.py

from typing import List, Optional
from uuid import UUID
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.shared.models.user import ADMIN_ROLE, User


class UserRepository:
    """Data access for User model."""

    def __init__(self, db: Session):
        self.db = db

    def get_user(self, user_id: UUID) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def list_users(
        self,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[User]:
        query = self.db.query(User)
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    User.email.ilike(pattern),
                    User.full_name.ilike(pattern),
                )
            )
        return (
            query.order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def create_user(
        self,
        email: str,
        full_name: Optional[str],
        password_hash: str,
        role: Optional[str] = None,
    ) -> User:
        user = User(email=email, full_name=full_name, password_hash=password_hash)
        if role is not None:
            user.role = role
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def admin_exists(self) -> bool:
        return self.db.query(User.id).filter(User.role == ADMIN_ROLE).first() is not None
