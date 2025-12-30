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
    
    def detach_resource(
        self,
        message_id: UUID,
        resource_id: UUID,
    ) -> None:
        att = (
            self.db.query(MessageAttachment)
            .filter(
                MessageAttachment.message_id == message_id,
                MessageAttachment.resource_id == resource_id,
            )
            .first()
        )
        if att:
            self.db.delete(att)
            self.db.commit()

    def get_message_resources(self, message_id: UUID) -> List[MessageAttachment]:
        return (
            self.db.query(MessageAttachment)
            .filter(MessageAttachment.message_id == message_id)
            .order_by(MessageAttachment.created_at.asc())
            .all()
        )

    def delete_attachments_by_session_id(self, session_id: UUID, *, commit: bool = False) -> int:
        """Bulk delete all attachments for messages belonging to a session."""
        from app.shared.models.message import Message
        count = (
            self.db.query(MessageAttachment)
            .filter(
                MessageAttachment.message_id.in_(
                    self.db.query(Message.id).filter(Message.session_id == session_id)
                )
            )
            .delete(synchronize_session=False)
        )
        if commit:
            self.db.commit()
        return count

    def get_resource_ids_for_session(self, session_id: UUID) -> List[UUID]:
        """Return resource IDs attached to any message in the session."""
        from app.shared.models.message import Message
        return [
            row[0]
            for row in self.db.query(MessageAttachment.resource_id)
            .filter(
                MessageAttachment.message_id.in_(
                    self.db.query(Message.id).filter(Message.session_id == session_id)
                )
            )
            .all()
        ]
