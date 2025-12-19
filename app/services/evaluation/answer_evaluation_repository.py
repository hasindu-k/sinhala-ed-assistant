# app/services/evaluation/answer_evaluation_repository.py

from typing import Optional, List, Dict
from uuid import UUID
from decimal import Decimal
from sqlalchemy.orm import Session

from app.shared.models.answer_evaluation import AnswerDocument, EvaluationResult, QuestionScore


class AnswerEvaluationRepository:
    """Data access layer for answer evaluation models."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_answer_document(
        self,
        evaluation_session_id: UUID,
        resource_id: UUID,
        student_identifier: Optional[str] = None
    ) -> AnswerDocument:
        """Create an answer document entry."""
        answer_doc = AnswerDocument(
            evaluation_session_id=evaluation_session_id,
            resource_id=resource_id,
            student_identifier=student_identifier
        )
        self.db.add(answer_doc)
        self.db.commit()
        self.db.refresh(answer_doc)
        return answer_doc
    
    def get_answer_document(self, answer_document_id: UUID) -> Optional[AnswerDocument]:
        """Get answer document by ID."""
        return self.db.query(AnswerDocument).filter(
            AnswerDocument.id == answer_document_id
        ).first()
    
    def get_answer_documents_by_evaluation_session(
        self,
        evaluation_session_id: UUID
    ) -> List[AnswerDocument]:
        """Get all answer documents for an evaluation session."""
        return self.db.query(AnswerDocument).filter(
            AnswerDocument.evaluation_session_id == evaluation_session_id
        ).all()
    
    def create_evaluation_result(
        self,
        answer_document_id: UUID,
        total_score: Optional[Decimal] = None,
        overall_feedback: Optional[str] = None
    ) -> EvaluationResult:
        """Create an evaluation result."""
        eval_result = EvaluationResult(
            answer_document_id=answer_document_id,
            total_score=total_score,
            overall_feedback=overall_feedback
        )
        self.db.add(eval_result)
        self.db.commit()
        self.db.refresh(eval_result)
        return eval_result
    
    def get_evaluation_result(self, evaluation_result_id: UUID) -> Optional[EvaluationResult]:
        """Get evaluation result by ID."""
        return self.db.query(EvaluationResult).filter(
            EvaluationResult.id == evaluation_result_id
        ).first()
    
    def get_evaluation_result_by_answer_document(
        self,
        answer_document_id: UUID
    ) -> Optional[EvaluationResult]:
        """Get evaluation result by answer document ID."""
        return self.db.query(EvaluationResult).filter(
            EvaluationResult.answer_document_id == answer_document_id
        ).first()
    
    def create_question_score(
        self,
        evaluation_result_id: UUID,
        sub_question_id: UUID,
        awarded_marks: Decimal,
        feedback: Optional[str] = None
    ) -> QuestionScore:
        """Create a score for a sub-question."""
        question_score = QuestionScore(
            evaluation_result_id=evaluation_result_id,
            sub_question_id=sub_question_id,
            awarded_marks=awarded_marks,
            feedback=feedback
        )
        self.db.add(question_score)
        self.db.commit()
        self.db.refresh(question_score)
        return question_score
    
    def get_question_scores_by_result(
        self,
        evaluation_result_id: UUID
    ) -> List[QuestionScore]:
        """Get all question scores for an evaluation result."""
        return self.db.query(QuestionScore).filter(
            QuestionScore.evaluation_result_id == evaluation_result_id
        ).all()
    
    def update_evaluation_result(
        self,
        evaluation_result_id: UUID,
        total_score: Optional[Decimal] = None,
        overall_feedback: Optional[str] = None
    ) -> Optional[EvaluationResult]:
        """Update evaluation result."""
        result = self.get_evaluation_result(evaluation_result_id)
        if result:
            if total_score is not None:
                result.total_score = total_score
            if overall_feedback is not None:
                result.overall_feedback = overall_feedback
            self.db.commit()
            self.db.refresh(result)
        return result
