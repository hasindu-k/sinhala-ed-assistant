from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.components.evaluation.temporary.temporary_schemas import TemporaryEvaluationInput, TemporaryEvaluationOutput
from app.components.evaluation.temporary.temporary_evaluation_service import TemporaryEvaluationService
from app.core.database import get_db
from app.core.security import get_current_user
from app.shared.models.user import User
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/evaluate", response_model=TemporaryEvaluationOutput)
def temporary_evaluate(
    input_data: TemporaryEvaluationInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Temporary endpoint for evaluation with detailed question structure and multiple students.
    Accepts syllabus text, paper parts with main/sub questions and marks, student answers with answered questions.
    Returns detailed evaluation results per student, including scores per subquestion, main question, and part.
    """
    service = TemporaryEvaluationService()
    try:
        result = service.evaluate_with_plain_text(input_data)
        return result
    except Exception as exc:
        logger.error(f"Failed temporary evaluation: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to perform temporary evaluation")