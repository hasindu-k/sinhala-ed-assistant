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

from app.shared.models.answer_evaluation import AnswerDocument, EvaluationResult, QuestionScore


def create_answer_document(
    *,
    db: Session,
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
    db.add(answer_doc)
    db.commit()
    db.refresh(answer_doc)
    return answer_doc


def get_answer_document(
    *,
    db: Session,
    answer_document_id: UUID
) -> Optional[AnswerDocument]:
    """Get answer document by ID."""
    return db.query(AnswerDocument).filter(
        AnswerDocument.id == answer_document_id
    ).first()


def get_answer_documents_by_evaluation_session(
    *,
    db: Session,
    evaluation_session_id: UUID
) -> List[AnswerDocument]:
    """Get all answer documents for an evaluation session."""
    return db.query(AnswerDocument).filter(
        AnswerDocument.evaluation_session_id == evaluation_session_id
    ).all()


def create_evaluation_result(
    *,
    db: Session,
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
    db.add(eval_result)
    db.commit()
    db.refresh(eval_result)
    return eval_result


def get_evaluation_result(
    *,
    db: Session,
    evaluation_result_id: UUID
) -> Optional[EvaluationResult]:
    """Get evaluation result by ID."""
    return db.query(EvaluationResult).filter(
        EvaluationResult.id == evaluation_result_id
    ).first()


def get_evaluation_result_by_answer_document(
    *,
    db: Session,
    answer_document_id: UUID
) -> Optional[EvaluationResult]:
    """Get evaluation result by answer document ID."""
    return db.query(EvaluationResult).filter(
        EvaluationResult.answer_document_id == answer_document_id
    ).first()


def create_question_score(
    *,
    db: Session,
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
    db.add(question_score)
    db.commit()
    db.refresh(question_score)
    return question_score


def get_question_scores_by_result(
    *,
    db: Session,
    evaluation_result_id: UUID
) -> List[QuestionScore]:
    """Get all question scores for an evaluation result."""
    return db.query(QuestionScore).filter(
        QuestionScore.evaluation_result_id == evaluation_result_id
    ).all()


def update_evaluation_result(
    *,
    db: Session,
    evaluation_result_id: UUID,
    total_score: Optional[Decimal] = None,
    overall_feedback: Optional[str] = None
) -> Optional[EvaluationResult]:
    """Update evaluation result."""
    result = get_evaluation_result(db=db, evaluation_result_id=evaluation_result_id)
    if result:
        if total_score is not None:
            result.total_score = total_score
        if overall_feedback is not None:
            result.overall_feedback = overall_feedback
        db.commit()
        db.refresh(result)
    return result


def create_complete_evaluation(
    *,
    db: Session,
    answer_document_id: UUID,
    scores: List[Dict],
    overall_feedback: Optional[str] = None
) -> EvaluationResult:
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
    
    eval_result = create_evaluation_result(
        db=db,
        answer_document_id=answer_document_id,
        total_score=total_score,
        overall_feedback=overall_feedback
    )
    
    for score_data in scores:
        create_question_score(
            db=db,
            evaluation_result_id=eval_result.id,
            sub_question_id=score_data["sub_question_id"],
            awarded_marks=Decimal(str(score_data["awarded_marks"])),
            feedback=score_data.get("feedback")
        )
    
    return eval_result


def get_complete_evaluation_result(
    *,
    db: Session,
    evaluation_result_id: UUID
) -> Optional[Dict]:
    """Get complete evaluation result with all question scores."""
    result = get_evaluation_result(db=db, evaluation_result_id=evaluation_result_id)
    if not result:
        return None
    
    scores = get_question_scores_by_result(db=db, evaluation_result_id=evaluation_result_id)
    
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