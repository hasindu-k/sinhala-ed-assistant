# app/repositories/processing_log_repository.py

from typing import List, Optional, Any, Dict
from uuid import UUID
from sqlalchemy.orm import Session

from app.shared.models.processing_log import ProcessingLog


class ProcessingLogRepository:
    """Data access for ProcessingLog."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        resource_id: UUID,
        stage: str,
        progress: float,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
        message_id: Optional[UUID] = None,
        *,
        commit: bool = False,
    ) -> ProcessingLog:
        log = ProcessingLog(
            resource_id=resource_id,
            user_id=user_id,
            session_id=session_id,
            message_id=message_id,
            stage=stage,
            progress=progress,
            details=details,
        )
        self.db.add(log)
        if commit:
            self.db.commit()
            self.db.refresh(log)
        return log

    def get_logs_for_resource(self, resource_id: UUID) -> List[ProcessingLog]:
        return (
            self.db.query(ProcessingLog)
            .filter(ProcessingLog.resource_id == resource_id)
            .order_by(ProcessingLog.timestamp.asc())
            .all()
        )

    def get_logs_for_message(self, message_id: UUID) -> List[ProcessingLog]:
        return (
            self.db.query(ProcessingLog)
            .filter(ProcessingLog.message_id == message_id)
            .order_by(ProcessingLog.timestamp.asc())
            .all()
        )
