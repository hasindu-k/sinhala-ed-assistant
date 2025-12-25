from typing import List
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.session_resource_repository import SessionResourceRepository


class SessionResourceService:
    """Business logic for session-resource linking."""

    def __init__(self, db: Session):
        self.repository = SessionResourceRepository(db)

    def attach_resource_to_session(self, session_id: UUID, resource_id: UUID):
        return self.repository.attach_resource_to_session(session_id, resource_id)

    def get_session_resources(self, session_id: UUID) -> List:
        return self.repository.get_session_resources(session_id)

    def detach_all_resources(self, session_id: UUID) -> int:
        return self.repository.delete_resources_for_session(session_id)
