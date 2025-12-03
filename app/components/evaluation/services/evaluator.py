# app/components/evaluation/services/evaluator.py

from sqlalchemy.orm import Session

from models.syllabus import Syllabus
from models.question import Question
from models.rubric import Rubric
from models.marks import Marks
from models.paper_settings import PaperSettings

from components.evaluation.schemas.evaluation_schema import (
    FinalEvaluationResponse,
    SubQuestionResult
)

from components.evaluation.services.scorer import compute_scores_for_answer
from components.evaluation.services.feedback import (
    generate_feedback_for_answer,
    generate_overall_feedback
)

from components.evaluation.utils.helpers import (
    extract_main_question_id,
    select_best_main_questions
)


# ------------------------------------------------------------
# MAIN PIPELINE
# ------------------------------------------------------------
def run_evaluation(teacher_id: str, student_answers: dict, language: str, db: Session):

    # ------------------------------------------------------------
    # 1. Load saved teacher configuration
    # ------------------------------------------------------------
    syllabus = db.query(Syllabus).filter_by(teacher_id=teacher_id).first()
    questions = db.query(Question).filter_by(teacher_id=teacher_id).first()
    rubric = db.query(Rubric).filter_by(teacher_id=teacher_id).first()
    marks = db.query(Marks).filter_by(teacher_id=teacher_id).first()
    paper = db.query(PaperSettings).filter_by(teacher_id=teacher_id).first()

    if not syllabus or not questions or not rubric or not marks or not paper:
        raise Exception("Teacher configuration incomplete. All uploads required.")

    syllabus_chunks = syllabus.syllabus_chunks
    question_dict = questions.questions
    marks_distribution = marks.marks_distribution

    rubric_weights = {
        "semantic_weight": rubric.semantic_weight,
        "coverage_weight": rubric.coverage_weight,
        "bm25_weight": rubric.bm25_weight
    }

    # ------------------------------------------------------------
    # 2. Score all subquestions (only those with answers)
    # ------------------------------------------------------------
    results = {}

    for qid, student_ans in student_answers.items():

        if qid not in question_dict:
            # unknown question id in student answers
            continue

        question_text = question_dict[qid]

        score_info = compute_scores_for_answer(
            question_text=question_text,
            student_answer=student_ans,
            syllabus_chunks=syllabus_chunks,
            rubric=rubric_weights,
            marks_distribution=marks_distribution,
            qid=qid
        )

        # Generate feedback for this subquestion
        feedback_text = generate_feedback_for_answer(
            qid=qid,
            student_answer=student_ans,
            score_details=score_info,
            language=language
        )

        # Build a result object
        sub_result = SubQuestionResult(
            question_id=qid,
            student_answer=student_ans,
            retrieved_context=score_info["retrieved_context"],
            semantic_score=score_info["semantic"],
            coverage_score=score_info["coverage"],
            bm25_score=score_info["bm25"],
            allocated_marks=score_info["allocated_marks"],
            total_score=score_info["final_score"],
            max_score=score_info["max_score"],
            feedback=feedback_text
        )

        results[qid] = sub_result

    # ------------------------------------------------------------
    # 3. Group subquestions under main question
    # ------------------------------------------------------------
    grouped = {}

    for qid, res in results.items():
        main_id = extract_main_question_id(qid)
        grouped.setdefault(main_id, []).append(res)

    # ------------------------------------------------------------
    # 4. Select the BEST N main questions (required_main_questions)
    # ------------------------------------------------------------
    selected_main_ids = select_best_main_questions(
        grouped,
        paper.required_main_questions
    )

    # ------------------------------------------------------------
    # 5. Compute final score (sum only selected main questions)
    # ------------------------------------------------------------
    final_score = 0

    for main_id in selected_main_ids:
        for sub_result in grouped[main_id]:
            final_score += sub_result.total_score

    # Cap at total_marks
    final_score = min(final_score, paper.total_marks)

    # ------------------------------------------------------------
    # 6. Overall feedback (large LLM)
    # ------------------------------------------------------------
    overall_feedback = generate_overall_feedback(
        results=results,
        final_score=final_score,
        max_score=paper.total_marks,
        language=language
    )

    # ------------------------------------------------------------
    # 7. Build final response object
    # ------------------------------------------------------------
    return FinalEvaluationResponse(
        results=results,
        selected_main_questions=selected_main_ids,
        final_score_obtained=final_score,
        final_score_total=paper.total_marks,
        overall_feedback=overall_feedback,
        per_question_feedback={qid: res.feedback for qid, res in results.items()}
    )
