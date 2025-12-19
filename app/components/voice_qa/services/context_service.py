from sqlalchemy.orm import Session
from app.models.message_attachment import MessageAttachment
from app.models.session_resource import SessionResource


def get_allowed_resource_ids(
    db: Session,
    session_id,
    message_id,
):
    """
    Priority:
    1. Files attached to this message
    2. Files attached to the session
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
