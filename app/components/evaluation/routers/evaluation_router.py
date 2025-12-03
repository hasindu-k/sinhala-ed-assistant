# app/components/evaluation/routers/evaluation_router.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db

from app.components.evaluation.schemas.evaluation_schema import (
    SyllabusUpload,
    QuestionUpload,
    RubricUpload,
    MarksUpload,
    PaperSettingsUpload,
    EvaluationRequest,
    FinalEvaluationResponse
)

from app.core.database import get_db

from app.shared.models.syllabus import Syllabus
from app.shared.models.question import Question
from app.shared.models.rubric import Rubric
from app.shared.models.marks import Marks
from app.shared.models.paper_settings import PaperSettings

from app.components.evaluation.services.evaluator import run_evaluation


router = APIRouter(prefix="/evaluation", tags=["Evaluation"])



# ------------------------------------------------------------
#  UPLOAD: SYLLABUS
# ------------------------------------------------------------
@router.post("/upload/syllabus")
def upload_syllabus(payload: SyllabusUpload, db: Session = Depends(get_db)):

    existing = db.query(Syllabus).filter_by(teacher_id=payload.teacher_id).first()

    if existing:
        existing.syllabus_chunks = payload.syllabus_chunks
    else:
        db.add(Syllabus(
            teacher_id=payload.teacher_id,
            syllabus_chunks=payload.syllabus_chunks
        ))

    db.commit()

    return {"status": "success", "message": "Syllabus uploaded successfully"}



# ------------------------------------------------------------
#  UPLOAD: QUESTIONS
# ------------------------------------------------------------
@router.post("/upload/questions")
def upload_questions(payload: QuestionUpload, db: Session = Depends(get_db)):

    existing = db.query(Question).filter_by(teacher_id=payload.teacher_id).first()

    if existing:
        existing.questions = payload.questions
    else:
        db.add(Question(
            teacher_id=payload.teacher_id,
            questions=payload.questions
        ))

    db.commit()

    return {"status": "success", "message": "Questions uploaded successfully"}



# ------------------------------------------------------------
#  UPLOAD: RUBRIC (GLOBAL)
# ------------------------------------------------------------
@router.post("/upload/rubric")
def upload_rubric(payload: RubricUpload, db: Session = Depends(get_db)):

    existing = db.query(Rubric).filter_by(teacher_id=payload.teacher_id).first()

    if existing:
        existing.semantic_weight = payload.semantic_weight
        existing.coverage_weight = payload.coverage_weight
        existing.bm25_weight = payload.bm25_weight
    else:
        db.add(Rubric(
            teacher_id=payload.teacher_id,
            semantic_weight=payload.semantic_weight,
            coverage_weight=payload.coverage_weight,
            bm25_weight=payload.bm25_weight
        ))

    db.commit()

    return {"status": "success", "message": "Rubric uploaded successfully"}



# ------------------------------------------------------------
#  UPLOAD: MARKS DISTRIBUTION (GLOBAL)
# ------------------------------------------------------------
# ------------------------------------------------------------
#  UPLOAD: MARKS DISTRIBUTION (GLOBAL – ONE ARRAY FOR ALL QUESTIONS)
# ------------------------------------------------------------
@router.post("/upload/marks")
def upload_marks(payload: MarksUpload, db: Session = Depends(get_db)):

    # Check paper settings to validate number of subquestions
    paper = db.query(PaperSettings).filter_by(teacher_id=payload.teacher_id).first()

    if paper:
        if len(payload.marks_distribution) != paper.subquestions_per_main:
            raise HTTPException(
                status_code=400,
                detail=f"Marks array must have {paper.subquestions_per_main} values."
            )

    # Store a single universal marks list (e.g., [3,3,6,8])
    existing = db.query(Marks).filter_by(teacher_id=payload.teacher_id).first()

    if existing:
        existing.marks_distribution = payload.marks_distribution
    else:
        db.add(Marks(
            teacher_id=payload.teacher_id,
            marks_distribution=payload.marks_distribution
        ))

    db.commit()

    return {"status": "success", "message": "Marks distribution uploaded successfully"}




# ------------------------------------------------------------
#  UPLOAD: PAPER SETTINGS
# ------------------------------------------------------------
@router.post("/upload/paper-settings")
def upload_paper_settings(payload: PaperSettingsUpload, db: Session = Depends(get_db)):

    if payload.required_main_questions > payload.total_main_questions:
        raise HTTPException(
            status_code=400,
            detail="required_main_questions cannot exceed total_main_questions."
        )

    existing = db.query(PaperSettings).filter_by(teacher_id=payload.teacher_id).first()

    if existing:
        existing.total_marks = payload.total_marks
        existing.total_main_questions = payload.total_main_questions
        existing.required_main_questions = payload.required_main_questions
        existing.subquestions_per_main = payload.subquestions_per_main

    else:
        db.add(PaperSettings(
            teacher_id=payload.teacher_id,
            total_marks=payload.total_marks,
            total_main_questions=payload.total_main_questions,
            required_main_questions=payload.required_main_questions,
            subquestions_per_main=payload.subquestions_per_main
        ))

    db.commit()

    return {"status": "success", "message": "Paper settings uploaded successfully"}



# ------------------------------------------------------------
#  MAIN EVALUATION ENDPOINT
# ------------------------------------------------------------
@router.post("/evaluate", response_model=FinalEvaluationResponse)
def evaluate(payload: EvaluationRequest, db: Session = Depends(get_db)):

    result = run_evaluation(
        teacher_id=payload.teacher_id,
        student_answers=payload.student_answers,
        language=payload.language,
        db=db
    )

    return result
