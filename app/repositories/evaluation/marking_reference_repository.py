# app/repositories/evaluation/marking_reference_repository.py

from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from app.shared.models.answer_evaluation import MarkingReference


class MarkingReferenceRepository:
    """Data access layer for marking references."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_reference(
        self,
        evaluation_session_id: UUID,
        question_id: Optional[UUID] = None,
        sub_question_id: Optional[UUID] = None,
        question_number: Optional[str] = None,
        question_text: Optional[str] = None,
        reference_answer: Optional[str] = None
    ) -> MarkingReference:
        """Create a new marking reference."""
        ref = MarkingReference(
            evaluation_session_id=evaluation_session_id,
            question_id=question_id,
            sub_question_id=sub_question_id,
            question_number=question_number,
            question_text=question_text,
            reference_answer=reference_answer,
            is_approved=False
        )
        self.db.add(ref)
        self.db.commit()
        self.db.refresh(ref)
        return ref
    
    def get_references_by_session(self, evaluation_session_id: UUID) -> List[MarkingReference]:
        """Get all references for a session."""
        return self.db.query(MarkingReference).filter(
            MarkingReference.evaluation_session_id == evaluation_session_id
        ).order_by(MarkingReference.created_at.asc()).all()
    
    def get_reference(self, reference_id: UUID) -> Optional[MarkingReference]:
        """Get a single reference by ID."""
        return self.db.query(MarkingReference).filter(MarkingReference.id == reference_id).first()
    
    def update_reference(self, reference_id: UUID, reference_answer: str) -> Optional[MarkingReference]:
        """Update the reference text."""
        ref = self.get_reference(reference_id)
        if ref:
            ref.reference_answer = reference_answer
            self.db.commit()
            self.db.refresh(ref)
        return ref
    
    def approve_session_references(self, evaluation_session_id: UUID):
        """Mark all references in a session as approved."""
        self.db.query(MarkingReference).filter(
            MarkingReference.evaluation_session_id == evaluation_session_id
        ).update({"is_approved": True})
        self.db.commit()

    def delete_session_references(self, evaluation_session_id: UUID):
        """Delete all references for a session (e.g. for re-extraction)."""
        self.db.query(MarkingReference).filter(
            MarkingReference.evaluation_session_id == evaluation_session_id
        ).delete()
        self.db.commit()
