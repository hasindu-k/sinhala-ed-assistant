from sqlalchemy.orm import Session
from typing import Dict, Any

from app.shared.models.syllabus import Syllabus
from app.shared.models.rubric import Rubric
from app.shared.models.paper_settings import PaperSettings
from app.shared.models.question_paper import UserQuestionPaper
from app.shared.models.user_answers import UserAnswers

from app.components.evaluation.schemas.evaluation_schema import (
    FinalEvaluationResponse,
    SubQuestionResult,
    MainQuestionResult,
)

from app.components.evaluation.services.scorer import (
    compute_scores_for_answer,
    build_bm25,
)

from app.components.evaluation.services.feedback import (
    generate_feedback_for_answer,
    generate_overall_feedback,
)

from app.components.evaluation.utils.helpers import (
    select_best_main_questions,
)


# ------------------------------------------------------------
# HELPER: Resolve Paper Structure (NO LEGACY FALLBACK)
# ------------------------------------------------------------
def _resolve_paper_structure(qp: UserQuestionPaper) -> Dict[str, Any]:
    """
    Authoritative: qp.paper_structure must exist.
    Legacy fallback has been removed to prevent hidden grading assumptions.
    """
    if qp.paper_structure:
        return qp.paper_structure

    raise Exception(
        "Paper structure not found. Upload the paper using /evaluation/upload/paper-structure "
        "so marks and subquestions are explicit."
    )


# ------------------------------------------------------------
# HELPER: Get Student Answer (Flat or Nested)
# ------------------------------------------------------------
def _get_student_answer(answers_source: Dict, main_id: str, sub_id: str) -> str:
    # 1) Nested: {"1": {"a": "..." }}
    try:
        if str(main_id) in answers_source:
            m_block = answers_source[str(main_id)]
            if isinstance(m_block, dict):
                return m_block.get(sub_id, "")
    except Exception:
        pass

    # 2) Flat: {"Q01_a": "..."}
    try:
        qid = f"Q{int(main_id):02d}_{sub_id}"
        if qid in answers_source:
            return answers_source[qid]
    except Exception:
        pass

    return ""


# ------------------------------------------------------------
# MAIN PIPELINE
# ------------------------------------------------------------
def run_evaluation(user_id: str, student_answers: dict, language: str, db: Session):
    syllabus = db.query(Syllabus).filter_by(user_id=user_id).first()
    qp = db.query(UserQuestionPaper).filter_by(user_id=user_id).first()
    rubric = db.query(Rubric).filter_by(user_id=user_id).first()
    settings = db.query(PaperSettings).filter_by(user_id=user_id).first()

    if not all([syllabus, qp, rubric, settings]):
        raise Exception("Teacher configuration incomplete. Missing Syllabus, Paper, Rubric, or Settings.")

    paper_structure = _resolve_paper_structure(qp)

    syllabus_chunks = syllabus.syllabus_chunks
    rubric_weights = {
        "semantic_weight": rubric.semantic_weight,
        "coverage_weight": rubric.coverage_weight,
        "bm25_weight": rubric.bm25_weight,
    }

    # --------------------------------------------------------
    # Answers source (DB preferred)
    # --------------------------------------------------------
    answers_row = db.query(UserAnswers).filter_by(user_id=user_id).first()
    if answers_row and answers_row.answers:
        answers_source = answers_row.answers
    else:
        answers_source = student_answers or {}

    # --------------------------------------------------------
    # Build BM25
    # --------------------------------------------------------
    bm25 = build_bm25(syllabus_chunks)

    # --------------------------------------------------------
    # Score Subquestions (Driven by PaperStructure)
    # --------------------------------------------------------
    results = {}
    main_questions_map = paper_structure.get("main_questions", {})

    for m_id, m_data in main_questions_map.items():
        sub_qs = m_data.get("subquestions", {})

        for s_id, s_data in sub_qs.items():
            qid = f"Q{int(m_id):02d}_{s_id}"
            q_text = s_data.get("text", "")
            allocated = float(s_data.get("marks", 0.0))

            ans_text = _get_student_answer(answers_source, m_id, s_id).strip()

            if not ans_text:
                sub_result = SubQuestionResult(
                    question_id=qid,
                    student_answer="",
                    retrieved_context=[],
                    semantic_score=0.0,
                    coverage_score=0.0,
                    bm25_score=0.0,
                    allocated_marks=allocated,
                    total_score=0.0,
                    max_score=allocated,
                    feedback="No answer provided.",
                )
            else:
                score_info = compute_scores_for_answer(
                    question_text=q_text,
                    student_answer=ans_text,
                    syllabus_chunks=syllabus_chunks,
                    rubric=rubric_weights,
                    allocated_marks=allocated,
                    bm25=bm25,
                )

                feedback_text = generate_feedback_for_answer(
                    qid=qid,
                    student_answer=ans_text,
                    score_details=score_info,
                    language=language,
                )

                sub_result = SubQuestionResult(
                    question_id=qid,
                    student_answer=ans_text,
                    retrieved_context=score_info["retrieved_context"],
                    semantic_score=score_info["semantic"],
                    coverage_score=score_info["coverage"],
                    bm25_score=score_info["bm25"],
                    allocated_marks=allocated,
                    total_score=score_info["final_score"],
                    max_score=allocated,
                    feedback=feedback_text,
                )

            results[qid] = sub_result

    # --------------------------------------------------------
    # Group by main question
    # --------------------------------------------------------
    grouped = {}
    main_results_objects = {}

    for qid, res in results.items():
        main_key = qid.split("_")[0]  # "Q01"
        grouped.setdefault(main_key, []).append(res)

    for main_key, sub_list in grouped.items():
        total_obtained = sum(r.total_score for r in sub_list)
        total_max = sum(r.max_score for r in sub_list)

        main_results_objects[main_key] = MainQuestionResult(
            main_question_id=main_key,
            sub_results=sub_list,
            question_total=total_obtained,
            question_max=total_max,
            selected=False,
        )

    # --------------------------------------------------------
    # Select best N (deterministic tie-breakers inside helper)
    # --------------------------------------------------------
    selected_main_ids = select_best_main_questions(grouped, settings.required_main_questions)

    for mid in selected_main_ids:
        if mid in main_results_objects:
            main_results_objects[mid].selected = True

    ignored_main_ids = [mid for mid in main_results_objects if not main_results_objects[mid].selected]

    # --------------------------------------------------------
    # Final score
    # --------------------------------------------------------
    final_score = sum(main_results_objects[mid].question_total for mid in selected_main_ids if mid in main_results_objects)
    final_score = min(final_score, float(settings.total_marks))

    # --------------------------------------------------------
    # Overall feedback (IMPORTANT FIX: pass ignored_main_questions)
    # --------------------------------------------------------
    overall_feedback = generate_overall_feedback(
        results=results,
        final_score=final_score,
        max_score=settings.total_marks,
        language=language,
        ignored_main_questions=ignored_main_ids,
    )

    return FinalEvaluationResponse(
        results=results,
        main_questions=main_results_objects,
        selected_main_questions=selected_main_ids,
        ignored_main_questions=ignored_main_ids,
        final_score_obtained=final_score,
        final_score_total=settings.total_marks,
        overall_feedback=overall_feedback,
        per_question_feedback={qid: res.feedback for qid, res in results.items()},
    )
