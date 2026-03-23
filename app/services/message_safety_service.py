# app/services/message_safety_service.py

from typing import Optional, Dict
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.message_safety_repository import MessageSafetyRepository


class MessageSafetyService:
    """Business logic for safety reports."""

    def __init__(self, db: Session):
        self.repository = MessageSafetyRepository(db)

    def create_safety_report(self, message_id: UUID, report_data: Dict):
        return self.repository.create_safety_report(message_id, report_data)

    def get_safety_report(self, message_id: UUID):
        return self.repository.get_safety_report(message_id)

    def get_safety_report_with_xai(self, message_id: UUID):
        # Currently same as get_safety_report but provided as explicit method for clarity
        return self.repository.get_safety_report(message_id)

    def get_only_xai_explanation(self, message_id: UUID):
        report = self.repository.get_safety_report(message_id)
        return report.xai_explanation if report else None