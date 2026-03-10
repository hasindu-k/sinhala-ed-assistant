# app/repositories/processing_log_repository.py

from typing import List, Optional, Any, Dict, Set
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

    def get_resource_ids_with_logs(self, resource_ids: List[UUID]) -> Set[UUID]:
        """Return the subset of resource_ids that have at least one processing log."""
        if not resource_ids:
            return set()
        rows = (
            self.db.query(ProcessingLog.resource_id)
            .filter(ProcessingLog.resource_id.in_(resource_ids))
            .distinct()
            .all()
        )
        return {row[0] for row in rows}

    def get_resource_message_ids(self, resource_ids: List[UUID]) -> Dict[UUID, UUID]:
        """Return a mapping of resource_id -> message_id for the first non-null message_id log per resource."""
        if not resource_ids:
            return {}
        rows = (
            self.db.query(ProcessingLog.resource_id, ProcessingLog.message_id)
            .filter(
                ProcessingLog.resource_id.in_(resource_ids),
                ProcessingLog.message_id.isnot(None),
            )
            .order_by(ProcessingLog.timestamp.asc())
            .all()
        )
        result: Dict[UUID, UUID] = {}
        for resource_id, message_id in rows:
            if resource_id not in result:
                result[resource_id] = message_id
        return result
