# app/services/evaluation/answer_evaluation_service.py

# Responsibility wise breakdown:
# create_answer_document	Register uploaded answer
# create_evaluation_result	Store overall result
# create_question_score	Store per-subquestion marks
# create_complete_evaluation	Orchestrates full evaluation
# get_complete_evaluation_result	Read model for UI

from typing import Optional, List, Dict
from uuid import UUID
from decimal import Decimal
from sqlalchemy.orm import Session

from app.services.evaluation.answer_evaluation_repository import AnswerEvaluationRepository


class AnswerEvaluationService:
    """Business logic for answer evaluation."""
    
    def __init__(self, db: Session):
        self.repository = AnswerEvaluationRepository(db)
    
    def create_answer_document(
        self,
        evaluation_session_id: UUID,
        resource_id: UUID,
        student_identifier: Optional[str] = None
    ):
        """Register an answer document."""
        return self.repository.create_answer_document(
            evaluation_session_id=evaluation_session_id,
            resource_id=resource_id,
            student_identifier=student_identifier
        )
    
    def get_answer_document(self, answer_document_id: UUID):
        """Get answer document by ID."""
        return self.repository.get_answer_document(answer_document_id)
    
    def get_answer_documents_by_evaluation_session(self, evaluation_session_id: UUID) -> List:
        """Get all answer documents for an evaluation session."""
        return self.repository.get_answer_documents_by_evaluation_session(evaluation_session_id)
    
    def create_evaluation_result(
        self,
        answer_document_id: UUID,
        total_score: Optional[Decimal] = None,
        overall_feedback: Optional[str] = None
    ):
        """Create an evaluation result."""
        return self.repository.create_evaluation_result(
            answer_document_id=answer_document_id,
            total_score=total_score,
            overall_feedback=overall_feedback
        )
    
    def get_evaluation_result(self, evaluation_result_id: UUID):
        """Get evaluation result by ID."""
        return self.repository.get_evaluation_result(evaluation_result_id)
    
    def get_evaluation_result_by_answer_document(self, answer_document_id: UUID):
        """Get evaluation result by answer document ID."""
        return self.repository.get_evaluation_result_by_answer_document(answer_document_id)
    
    def create_question_score(
        self,
        evaluation_result_id: UUID,
        sub_question_id: UUID,
        awarded_marks: Decimal,
        feedback: Optional[str] = None
    ):
        """Create a score for a sub-question."""
        return self.repository.create_question_score(
            evaluation_result_id=evaluation_result_id,
            sub_question_id=sub_question_id,
            awarded_marks=awarded_marks,
            feedback=feedback
        )
    
    def get_question_scores_by_result(self, evaluation_result_id: UUID) -> List:
        """Get all question scores for an evaluation result."""
        return self.repository.get_question_scores_by_result(evaluation_result_id)
    
    def update_evaluation_result(
        self,
        evaluation_result_id: UUID,
        total_score: Optional[Decimal] = None,
        overall_feedback: Optional[str] = None
    ):
        """Update evaluation result."""
        return self.repository.update_evaluation_result(
            evaluation_result_id=evaluation_result_id,
            total_score=total_score,
            overall_feedback=overall_feedback
        )
    
    def create_complete_evaluation(
        self,
        answer_document_id: UUID,
        scores: List[Dict],
        overall_feedback: Optional[str] = None
    ):
        """
        Create a complete evaluation with all question scores.
        
        scores format:
        [
            {
                "sub_question_id": UUID,
                "awarded_marks": Decimal,
                "feedback": str (optional)
            }
        ]
        """
        total_score = sum(Decimal(str(score["awarded_marks"])) for score in scores)
        
        eval_result = self.repository.create_evaluation_result(
            answer_document_id=answer_document_id,
            total_score=total_score,
            overall_feedback=overall_feedback
        )
        
        for score_data in scores:
            self.repository.create_question_score(
                evaluation_result_id=eval_result.id,
                sub_question_id=score_data["sub_question_id"],
                awarded_marks=Decimal(str(score_data["awarded_marks"])),
                feedback=score_data.get("feedback")
            )
        
        return eval_result
    
    def get_complete_evaluation_result(self, evaluation_result_id: UUID) -> Optional[Dict]:
        """Get complete evaluation result with all question scores."""
        result = self.repository.get_evaluation_result(evaluation_result_id)
        if not result:
            return None
        
        scores = self.repository.get_question_scores_by_result(evaluation_result_id)
        
        return {
            "id": result.id,
            "answer_document_id": result.answer_document_id,
            "total_score": float(result.total_score) if result.total_score else None,
            "overall_feedback": result.overall_feedback,
            "evaluated_at": result.evaluated_at,
            "question_scores": [
                {
                    "id": score.id,
                    "sub_question_id": score.sub_question_id,
                    "awarded_marks": float(score.awarded_marks) if score.awarded_marks else None,
                    "feedback": score.feedback
                }
                for score in scores
            ]
        }