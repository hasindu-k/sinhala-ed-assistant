# app/components/evaluation/routers/evaluation_router.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

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

from app.shared.models.syllabus import Syllabus
from app.shared.models.question import Question
from app.shared.models.rubric import Rubric
from app.shared.models.marks import Marks
from app.shared.models.paper_settings import PaperSettings

from app.components.evaluation.services.evaluator import run_evaluation

from app.shared.models.paper_data import PaperData
from app.components.evaluation.utils.question_numbering import (
    normalize_ocr_text,
    build_numbered_questions
)
from app.components.evaluation.schemas.evaluation_schema import OCRProcessedUpload
from app.shared.models.question_paper import UserQuestionPaper
from app.components.evaluation.schemas.evaluation_schema import PaperUpload


router = APIRouter(prefix="/evaluation", tags=["Evaluation"])



# -----------------------------------------------------------------------------------
# UPLOAD SYLLABUS
# -----------------------------------------------------------------------------------
@router.post("/upload/syllabus")
def upload_syllabus(payload: SyllabusUpload, db: Session = Depends(get_db)):

    existing = db.query(Syllabus).filter_by(user_id=payload.user_id).first()

    if existing:
        existing.syllabus_chunks = payload.syllabus_chunks
    else:
        db.add(Syllabus(
            user_id=payload.user_id,
            syllabus_chunks=payload.syllabus_chunks
        ))

    db.commit()
    return {"status": "success", "message": "Syllabus uploaded successfully"}



# -----------------------------------------------------------------------------------
# UPLOAD QUESTIONS DIRECTLY (manual upload)
# -----------------------------------------------------------------------------------
@router.post("/upload/questions")
def upload_questions(payload: QuestionUpload, db: Session = Depends(get_db)):

    existing = db.query(Question).filter_by(user_id=payload.user_id).first()

    if existing:
        existing.questions = payload.questions
    else:
        db.add(Question(
            user_id=payload.user_id,
            questions=payload.questions
        ))

    db.commit()
    return {"status": "success", "message": "Questions uploaded successfully"}



# -----------------------------------------------------------------------------------
# NEW: UPLOAD QUESTIONS FROM OCR-PREVIEW OUTPUT
# -----------------------------------------------------------------------------------

class UploadFromPreviewRequest(BaseModel):
    user_id: str
    raw_text: str
    total_main_questions: int
    sub_questions_per_main: int


@router.post("/upload/questions-from-preview")
def upload_questions_from_preview(payload: UploadFromPreviewRequest,
                                  db: Session = Depends(get_db)):

    # 1. Build structured dict like {"Q01_a": "...", ...}
    structured = build_numbered_questions(
        raw_text=payload.raw_text,
        total_main=payload.total_main_questions,
        sub_count=payload.sub_questions_per_main
    )

    # 2. Store in DB
    existing = db.query(Question).filter_by(user_id=payload.user_id).first()

    if existing:
        existing.questions = structured
    else:
        db.add(Question(
            user_id=payload.user_id,
            questions=structured
        ))

    db.commit()

    return {
        "status": "success",
        "message": "OCR-numbered questions saved successfully",
        "stored_questions": structured
    }



# -----------------------------------------------------------------------------------
# UPLOAD RUBRIC
# -----------------------------------------------------------------------------------
@router.post("/upload/rubric")
def upload_rubric(payload: RubricUpload, db: Session = Depends(get_db)):

    existing = db.query(Rubric).filter_by(user_id=payload.user_id).first()

    if existing:
        existing.semantic_weight = payload.semantic_weight
        existing.coverage_weight = payload.coverage_weight
        existing.bm25_weight = payload.bm25_weight
    else:
        db.add(Rubric(
            user_id=payload.user_id,
            semantic_weight=payload.semantic_weight,
            coverage_weight=payload.coverage_weight,
            bm25_weight=payload.bm25_weight
        ))

    db.commit()
    return {"status": "success", "message": "Rubric uploaded successfully"}



# -----------------------------------------------------------------------------------
# UPLOAD MARKS
# -----------------------------------------------------------------------------------
@router.post("/upload/marks")
def upload_marks(payload: MarksUpload, db: Session = Depends(get_db)):

    paper = db.query(PaperSettings).filter_by(user_id=payload.user_id).first()

    if paper and len(payload.marks_distribution) != paper.subquestions_per_main:
        raise HTTPException(
            status_code=400,
            detail=f"Marks array must have {paper.subquestions_per_main} values."
        )

    existing = db.query(Marks).filter_by(user_id=payload.user_id).first()

    if existing:
        existing.marks_distribution = payload.marks_distribution
    else:
        db.add(Marks(
            user_id=payload.user_id,
            marks_distribution=payload.marks_distribution
        ))

    db.commit()
    return {"status": "success", "message": "Marks distribution uploaded successfully"}



# -----------------------------------------------------------------------------------
# UPLOAD PAPER SETTINGS
# -----------------------------------------------------------------------------------
@router.post("/upload/paper-settings")
def upload_paper_settings(payload: PaperSettingsUpload, db: Session = Depends(get_db)):

    if payload.required_main_questions > payload.total_main_questions:
        raise HTTPException(
            status_code=400,
            detail="required_main_questions cannot exceed total_main_questions."
        )

    existing = db.query(PaperSettings).filter_by(user_id=payload.user_id).first()

    if existing:
        existing.total_marks = payload.total_marks
        existing.total_main_questions = payload.total_main_questions
        existing.required_main_questions = payload.required_main_questions
        existing.subquestions_per_main = payload.subquestions_per_main

    else:
        db.add(PaperSettings(
            user_id=payload.user_id,
            total_marks=payload.total_marks,
            total_main_questions=payload.total_main_questions,
            required_main_questions=payload.required_main_questions,
            subquestions_per_main=payload.subquestions_per_main
        ))

    db.commit()
    return {"status": "success", "message": "Paper settings uploaded successfully"}



# -----------------------------------------------------------------------------------
# PREVIEW (unchanged)
# -----------------------------------------------------------------------------------
class PreviewRequest(BaseModel):
    raw_text: str
    total_main_questions: int
    sub_questions_per_main: int


@router.post("/preview-questions")
def preview_questions(payload: PreviewRequest):

    structured = build_numbered_questions(
        raw_text=payload.raw_text,
        total_main=payload.total_main_questions,
        sub_count=payload.sub_questions_per_main
    )

    return {
        "status": "success",
        "structured_questions": structured
    }
# -----------------------------------------------------------------------------------
# ocr-processed structured questions upload
# -----------------------------------------------------------------------------------
@router.post("/upload/ocr-processed")
def upload_ocr_processed(payload: OCRProcessedUpload, db: Session = Depends(get_db)):

    # 1. Normalize OCR text
    cleaned = normalize_ocr_text(payload.raw_text)

    # 2. Auto-generate structured questions
    structured = build_numbered_questions(
        raw_text=cleaned,
        total_main=payload.total_main_questions,
        sub_count=payload.sub_questions_per_main
    )

    # 3. Save to DB
    existing = db.query(PaperData).filter_by(user_id=payload.user_id).first()

    if existing:
        existing.cleaned_text = cleaned
        existing.structured_questions = structured
    else:
        db.add(PaperData(
            user_id=payload.user_id,
            cleaned_text=cleaned,
            structured_questions=structured
        ))

    db.commit()

    return {
        "status": "success",
        "message": "OCR processed paper saved",
        "cleaned_text": cleaned[:300],
        "structured_questions_preview": structured
    }

# -----------------------------------------------------------------------------------
# OCR-paper storage + automatic structured question loading for evaluation.
# -----------------------------------------------------------------------------------

@router.post("/upload-paper")
def upload_question_paper(payload: PaperUpload, db: Session = Depends(get_db)):

    # 1. Normalize OCR text
    cleaned = normalize_ocr_text(payload.raw_text)

    # 2. Build structured numbered questions
    structured = build_numbered_questions(
        raw_text=cleaned,
        total_main=payload.total_main_questions,
        sub_count=payload.sub_questions_per_main
    )

    # 3. Save to DB (overwrite previous)
    existing = db.query(UserQuestionPaper).filter_by(user_id=payload.user_id).first()

    if existing:
        existing.raw_text = payload.raw_text
        existing.cleaned_text = cleaned
        existing.structured_questions = structured
        existing.total_main_questions = payload.total_main_questions
        existing.sub_questions_per_main = payload.sub_questions_per_main
    else:
        db.add(UserQuestionPaper(
            user_id=payload.user_id,
            raw_text=payload.raw_text,
            cleaned_text=cleaned,
            structured_questions=structured,
            total_main_questions=payload.total_main_questions,
            sub_questions_per_main=payload.sub_questions_per_main
        ))

    db.commit()

    return {
        "status": "success",
        "structured_questions": structured
    }

# -----------------------------------------------------------------------------------
# EVALUATE
# -----------------------------------------------------------------------------------
@router.post("/evaluate", response_model=FinalEvaluationResponse)
def evaluate(payload: EvaluationRequest, db: Session = Depends(get_db)):

    result = run_evaluation(
        user_id=payload.user_id,
        student_answers=payload.student_answers,
        language=payload.language,
        db=db
    )

    return result
