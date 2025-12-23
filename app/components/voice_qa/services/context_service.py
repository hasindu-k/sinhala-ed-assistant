import uuid
from sqlalchemy.orm import Session
from uuid import UUID

from app.shared.models.message_relations import MessageAttachment
from app.shared.models.session_resources import SessionResource


def get_allowed_resource_ids(
    *,
    db: Session,
    session_id: UUID,
    message_id: UUID,
):
    """
    Priority:
    1. Message-level attachments
    2. Session-level resources
    """

    # 1️⃣ message-level attachments
    rows = (
        db.query(MessageAttachment.resource_id)
        .filter(MessageAttachment.message_id == message_id)
        .all()
    )

    if rows:
        return [r.resource_id for r in rows]

    # 2️⃣ session-level resources
    rows = (
        db.query(SessionResource.resource_id)
        .filter(SessionResource.session_id == session_id)
        .all()
    )

    return [r.resource_id for r in rows]

def attach_resource_to_message(
    *,
    db: Session,
    message_id: UUID,
    resource_id: UUID,
    attachment_type: str = "resource",
):
    attachment = MessageAttachment(
        id=uuid.uuid4(),
        message_id=message_id,
        resource_id=resource_id,
        attachment_type=attachment_type,
    )
    db.add(attachment)
    db.commit()

