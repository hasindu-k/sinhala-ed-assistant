# app/repositories/message_attachment_repository.py

from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.shared.models.message_relations import MessageAttachment


class MessageAttachmentRepository:
    """Data access for MessageAttachment."""

    def __init__(self, db: Session):
        self.db = db

    def attach_resource(
        self,
        message_id: UUID,
        resource_id: UUID,
        display_name: Optional[str] = None,
        attachment_type: Optional[str] = None,
    ) -> MessageAttachment:
        att = MessageAttachment(
            message_id=message_id,
            resource_id=resource_id,
            display_name=display_name,
            attachment_type=attachment_type,
        )
        self.db.add(att)
        self.db.commit()
        self.db.refresh(att)
        return att

    def get_message_resources(self, message_id: UUID) -> List[MessageAttachment]:
        return (
            self.db.query(MessageAttachment)
            .filter(MessageAttachment.message_id == message_id)
            .order_by(MessageAttachment.created_at.asc())
            .all()
        )
