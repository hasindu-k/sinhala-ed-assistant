from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.services.resource_repository import ResourceRepository


class ResourceService:
    """Business logic for resources (files)."""

    def __init__(self, db: Session):
        self.repository = ResourceRepository(db)

    def upload_resource(
        self,
        user_id: UUID,
        original_filename: Optional[str],
        storage_path: Optional[str],
        mime_type: Optional[str],
        size_bytes: Optional[int],
        source_type: Optional[str] = None,
        language: Optional[str] = None,
    ):
        return self.repository.upload_resource(
            user_id=user_id,
            original_filename=original_filename,
            storage_path=storage_path,
            mime_type=mime_type,
            size_bytes=size_bytes,
            source_type=source_type,
            language=language,
        )

    def get_resource(self, resource_id: UUID):
        return self.repository.get_resource(resource_id)

    def list_user_resources(self, user_id: UUID) -> List:
        return self.repository.list_user_resources(user_id)
