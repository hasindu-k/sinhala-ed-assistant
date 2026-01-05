# app/repositories/session_resource_repository.py

from typing import List
from uuid import UUID
from sqlalchemy.orm import Session

from app.shared.models.session_resources import SessionResource
from app.shared.models.resource_file import ResourceFile


class SessionResourceRepository:
    """Data access for SessionResource link table."""

    def __init__(self, db: Session):
        self.db = db

    def attach_resource_to_session(self, session_id: UUID, resource_id: UUID) -> SessionResource:
        link = SessionResource(session_id=session_id, resource_id=resource_id)
        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)
        return link

    def get_session_resources(self, session_id: UUID) -> List[SessionResource]:
        return (
            self.db.query(SessionResource)
            .filter(SessionResource.session_id == session_id)
            .all()
        )

    def get_resources_by_session_id(self, session_id: UUID) -> List[ResourceFile]:
        return (
            self.db.query(ResourceFile)
            .join(SessionResource, SessionResource.resource_id == ResourceFile.id)
            .filter(SessionResource.session_id == session_id)
            .all()
        )

    def delete_resources_for_session(self, session_id: UUID) -> int:
        rows = (
            self.db.query(SessionResource)
            .filter(SessionResource.session_id == session_id)
            .delete()
        )
        self.db.commit()
        return rows
