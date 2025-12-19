from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db

# Schemas
from app.components.evaluation.schemas.evaluation_schema import (
    SyllabusUpload,
    QuestionUpload,
    RubricUpload,
    MarksUpload,
    PaperSettingsUpload,
    EvaluationRequest,
    FinalEvaluationResponse,
    OCRProcessedUpload,
    PaperUpload,
    AnswerUpload,
    PaperStructureUpload,
)

# DB Models
from app.shared.models.syllabus import Syllabus
from app.shared.models.question import Question
from app.shared.models.rubric import Rubric
from app.shared.models.marks import Marks
from app.shared.models.paper_settings import PaperSettings
from app.shared.models.paper_data import PaperData
from app.shared.models.question_paper import UserQuestionPaper
from app.shared.models.user_answers import UserAnswers

# Parsing utils
from app.components.evaluation.utils.question_numbering import build_numbered_questions
from app.components.evaluation.utils.answer_numbering import build_numbered_answers

# Evaluator
from app.components.evaluation.services.evaluator import run_evaluation

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])


# =====================================================================
# 1. Upload syllabus
# =====================================================================
@router.post("/upload/syllabus")
def upload_syllabus(payload: SyllabusUpload, db: Session = Depends(get_db)):
    existing = db.query(Syllabus).filter_by(user_id=payload.user_id).first()

    if existing:
        existing.syllabus_chunks = payload.syllabus_chunks
    else:
        db.add(Syllabus(user_id=payload.user_id, syllabus_chunks=payload.syllabus_chunks))

    db.commit()
    return {"status": "success", "message": "Syllabus uploaded successfully"}


# =====================================================================
# 2. Manual question upload (developer use)
# =====================================================================
@router.post("/upload/questions")
def upload_questions(payload: QuestionUpload, db: Session = Depends(get_db)):
    existing = db.query(Question).filter_by(user_id=payload.user_id).first()

    if existing:
        existing.questions = payload.questions
    else:
        db.add(Question(user_id=payload.user_id, questions=payload.questions))

    db.commit()
    return {"status": "success", "message": "Questions uploaded successfully"}


# =====================================================================
# 3. Upload questions (from OCR Preview)
# NOTE: preview-only still uses total_main + sub_questions_per_main
# =====================================================================
class UploadFromPreviewRequest(BaseModel):
    user_id: str
    raw_text: str
    total_main_questions: int
    sub_questions_per_main: int


@router.post("/upload/questions-from-preview")
def upload_questions_from_preview(payload: UploadFromPreviewRequest, db: Session = Depends(get_db)):
    structured = build_numbered_questions(
        raw_text=payload.raw_text,
        total_main=payload.total_main_questions,
        sub_count=payload.sub_questions_per_main,
    )

    existing = db.query(Question).filter_by(user_id=payload.user_id).first()
    if existing:
        existing.questions = structured
    else:
        db.add(Question(user_id=payload.user_id, questions=structured))

    db.commit()

    return {
        "status": "success",
        "message": "OCR-numbered questions saved successfully",
        "stored_questions": structured,
    }


# =====================================================================
# 4. Upload rubric
# =====================================================================
@router.post("/upload/rubric")
def upload_rubric(payload: RubricUpload, db: Session = Depends(get_db)):
    existing = db.query(Rubric).filter_by(user_id=payload.user_id).first()

    if existing:
        existing.semantic_weight = payload.semantic_weight
        existing.coverage_weight = payload.coverage_weight
        existing.bm25_weight = payload.bm25_weight
    else:
        db.add(
            Rubric(
                user_id=payload.user_id,
                semantic_weight=payload.semantic_weight,
                coverage_weight=payload.coverage_weight,
                bm25_weight=payload.bm25_weight,
            )
        )

    db.commit()
    return {"status": "success", "message": "Rubric uploaded successfully"}


# =====================================================================
# 5. Upload marks distribution (DEPRECATED)
# =====================================================================
@router.post("/upload/marks")
def upload_marks(payload: MarksUpload, db: Session = Depends(get_db)):
    existing = db.query(Marks).filter_by(user_id=payload.user_id).first()

    if existing:
        existing.marks_distribution = payload.marks_distribution
    else:
        db.add(Marks(user_id=payload.user_id, marks_distribution=payload.marks_distribution))

    db.commit()
    return {"status": "success", "message": "Marks uploaded successfully (DEPRECATED)"}


# =====================================================================
# 6. Upload paper settings
# =====================================================================
@router.post("/upload/paper-settings")
def upload_paper_settings(payload: PaperSettingsUpload, db: Session = Depends(get_db)):
    if payload.required_main_questions > payload.total_main_questions:
        raise HTTPException(
            status_code=400,
            detail="required_main_questions cannot exceed total_main_questions",
        )

    existing = db.query(PaperSettings).filter_by(user_id=payload.user_id).first()
    if existing:
        existing.total_marks = payload.total_marks
        existing.total_main_questions = payload.total_main_questions
        existing.required_main_questions = payload.required_main_questions
    else:
        db.add(
            PaperSettings(
                user_id=payload.user_id,
                total_marks=payload.total_marks,
                total_main_questions=payload.total_main_questions,
                required_main_questions=payload.required_main_questions,
            )
        )

    db.commit()
    return {"status": "success", "message": "Paper settings uploaded successfully"}


# =====================================================================
# 7. Preview structured questions (before saving)
# NOTE: preview-only still uses total_main + sub_questions_per_main
# =====================================================================
class PreviewRequest(BaseModel):
    raw_text: str
    total_main_questions: int
    sub_questions_per_main: int


@router.post("/preview-questions")
def preview_questions(payload: PreviewRequest):
    structured = build_numbered_questions(
        raw_text=payload.raw_text,
        total_main=payload.total_main_questions,
        sub_count=payload.sub_questions_per_main,
    )
    return {"status": "success", "structured_questions": structured}


# =====================================================================
# 8. Upload OCR-processed question paper (legacy helper, not authoritative)
# =====================================================================
@router.post("/upload/ocr-processed")
def upload_ocr_processed(payload: OCRProcessedUpload, db: Session = Depends(get_db)):
    cleaned = payload.raw_text.strip()

    structured = build_numbered_questions(
        raw_text=cleaned,
        total_main=payload.total_main_questions,
        sub_count=payload.sub_questions_per_main,
    )

    existing = db.query(PaperData).filter_by(user_id=payload.user_id).first()
    if existing:
        existing.cleaned_text = cleaned
        existing.structured_questions = structured
    else:
        db.add(PaperData(user_id=payload.user_id, cleaned_text=cleaned, structured_questions=structured))

    db.commit()

    return {
        "status": "success",
        "message": "OCR processed questions saved",
        "cleaned_text": cleaned[:300],
        "structured_questions_preview": structured,
    }


# =====================================================================
# 9. Upload paper structure (AUTHORITATIVE)
# =====================================================================
@router.post("/upload/paper-structure")
def upload_paper_structure(payload: PaperStructureUpload, db: Session = Depends(get_db)):
    """
    Authoritative source of truth for questions + marks.
    Also back-populates structured_questions for legacy compatibility.
    """

    flat_questions = {}
    structure_data = payload.paper_structure.dict()
    main_questions = structure_data.get("main_questions", {})

    for m_id, m_data in main_questions.items():
        sub_qs = m_data.get("subquestions", {})
        for s_id, s_data in sub_qs.items():
            try:
                m_num = int(m_id)
                qid = f"Q{m_num:02d}_{s_id}"
                flat_questions[qid] = s_data["text"]
            except ValueError:
                continue

    existing = db.query(UserQuestionPaper).filter_by(user_id=payload.user_id).first()
    if existing:
        existing.paper_structure = structure_data
        existing.structured_questions = flat_questions
        existing.total_main_questions = len(main_questions)
        # raw_text/cleaned_text are optional now; paper_structure is the truth
    else:
        db.add(
            UserQuestionPaper(
                user_id=payload.user_id,
                paper_structure=structure_data,
                structured_questions=flat_questions,
                total_main_questions=len(main_questions),
            )
        )

    db.commit()

    return {
        "status": "success",
        "message": "Paper structure (questions + marks) saved successfully",
        "questions_count": len(flat_questions),
    }


# =====================================================================
# Legacy endpoint: Prefer /upload/paper-structure
# =====================================================================
@router.post("/upload-paper")
def upload_question_paper(payload: PaperUpload, db: Session = Depends(get_db)):
    cleaned = payload.raw_text.strip()

    structured = build_numbered_questions(
        raw_text=cleaned,
        total_main=payload.total_main_questions,
        sub_count=payload.sub_questions_per_main,
    )

    existing = db.query(UserQuestionPaper).filter_by(user_id=payload.user_id).first()
    if existing:
        existing.raw_text = payload.raw_text
        existing.cleaned_text = cleaned
        existing.structured_questions = structured
        existing.total_main_questions = payload.total_main_questions
    else:
        db.add(
            UserQuestionPaper(
                user_id=payload.user_id,
                raw_text=payload.raw_text,
                cleaned_text=cleaned,
                structured_questions=structured,
                total_main_questions=payload.total_main_questions,
            )
        )

    db.commit()
    return {"status": "success", "structured_questions": structured}


# =====================================================================
# 10. Upload student answers
# =====================================================================
@router.post("/upload/answers")
def upload_answers(payload: AnswerUpload, db: Session = Depends(get_db)):
    settings = db.query(PaperSettings).filter_by(user_id=payload.user_id).first()
    if not settings:
        raise HTTPException(status_code=400, detail="Paper settings not found. Upload settings first.")

    # IMPORTANT CHANGE:
    # We no longer rely on settings.subquestions_per_main (removed from system logic).
    numbered = build_numbered_answers(
        raw_text=payload.raw_text,
        total_main_questions=settings.total_main_questions,
        subquestions_per_main=26,  # soft cap, supports variable structures
    )

    existing = db.query(UserAnswers).filter_by(user_id=payload.user_id).first()
    if existing:
        existing.answers = numbered
    else:
        db.add(UserAnswers(user_id=payload.user_id, answers=numbered))

    db.commit()

    return {
        "status": "success",
        "message": "Student answers stored successfully",
        "extracted_answers": numbered,
    }


# =====================================================================
# 11. Final evaluation
# =====================================================================
@router.post("/evaluate", response_model=FinalEvaluationResponse)
def evaluate(payload: EvaluationRequest, db: Session = Depends(get_db)):
    result = run_evaluation(
        user_id=payload.user_id,
        student_answers=payload.student_answers,
        language=payload.language,
        db=db,
    )
    return result
