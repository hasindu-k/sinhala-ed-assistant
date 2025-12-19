# app/services/resource_repository.py

from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.shared.models.resource_file import ResourceFile


class ResourceRepository:
    """Data access for ResourceFile."""

    def __init__(self, db: Session):
        self.db = db

    def upload_resource(
        self,
        user_id: UUID,
        original_filename: Optional[str],
        storage_path: Optional[str],
        mime_type: Optional[str],
        size_bytes: Optional[int],
        source_type: Optional[str] = None,
        language: Optional[str] = None,
    ) -> ResourceFile:
        res = ResourceFile(
            user_id=user_id,
            original_filename=original_filename,
            storage_path=storage_path,
            mime_type=mime_type,
            size_bytes=size_bytes,
            source_type=source_type,
            language=language,
        )
        self.db.add(res)
        self.db.commit()
        self.db.refresh(res)
        return res

    def get_resource(self, resource_id: UUID) -> Optional[ResourceFile]:
        return self.db.query(ResourceFile).filter(ResourceFile.id == resource_id).first()

    def list_user_resources(self, user_id: UUID) -> List[ResourceFile]:
        return (
            self.db.query(ResourceFile)
            .filter(ResourceFile.user_id == user_id)
            .order_by(ResourceFile.created_at.desc())
            .all()
        )
