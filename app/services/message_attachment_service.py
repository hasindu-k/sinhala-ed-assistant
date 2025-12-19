from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.message_attachment_repository import MessageAttachmentRepository


class MessageAttachmentService:
    """Business logic for message attachments."""

    def __init__(self, db: Session):
        self.repository = MessageAttachmentRepository(db)

    def attach_resource(
        self,
        message_id: UUID,
        resource_id: UUID,
        display_name: Optional[str] = None,
        attachment_type: Optional[str] = None,
    ):
        return self.repository.attach_resource(
            message_id=message_id,
            resource_id=resource_id,
            display_name=display_name,
            attachment_type=attachment_type,
        )

    def get_message_resources(self, message_id: UUID) -> List:
        return self.repository.get_message_resources(message_id)