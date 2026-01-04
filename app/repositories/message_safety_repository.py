# app/repositories/message_safety_repository.py

import json
from typing import Optional, Dict
from uuid import UUID
from sqlalchemy.orm import Session

from app.shared.models.message_relations import MessageSafetyReport


class MessageSafetyRepository:
    """Data access for MessageSafetyReport."""

    def __init__(self, db: Session):
        self.db = db

    def create_safety_report(self, message_id: UUID, report_data: Dict) -> MessageSafetyReport:
        row = MessageSafetyReport(
            message_id=message_id,
            missing_concepts=report_data.get("missing_concepts"),
            extra_concepts=report_data.get("extra_concepts"),
            flagged_sentences=report_data.get("flagged_sentences"),
            reasoning=report_data.get("reasoning"),
            # Persist computed summary values to database
            computed_severity=report_data.get("computed_severity"),
            computed_confidence_score=report_data.get("computed_confidence_score"),
            computed_reliability=report_data.get("computed_reliability"),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_safety_report(self, message_id: UUID) -> Optional[MessageSafetyReport]:
        return (
            self.db.query(MessageSafetyReport)
            .filter(MessageSafetyReport.message_id == message_id)
            .order_by(MessageSafetyReport.created_at.desc())
            .first()
        )