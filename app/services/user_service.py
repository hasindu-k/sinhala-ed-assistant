from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.user_repository import UserRepository


class UserService:
    """Business logic for users."""

    def __init__(self, db: Session):
        self.repository = UserRepository(db)

    def get_user(self, user_id: UUID):
        return self.repository.get_user(user_id)

    def get_user_by_email(self, email: str):
        return self.repository.get_user_by_email(email)

    def create_user(self, email: str, full_name: Optional[str], password_hash: str):
        return self.repository.create_user(email, full_name, password_hash)
