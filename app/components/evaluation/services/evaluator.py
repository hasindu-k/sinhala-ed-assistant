# app/components/evaluation/services/evaluator.py

from sqlalchemy.orm import Session

from app.shared.models.syllabus import Syllabus
from app.shared.models.question import Question
from app.shared.models.rubric import Rubric
from app.shared.models.marks import Marks
from app.shared.models.paper_settings import PaperSettings

from app.components.evaluation.schemas.evaluation_schema import (
    FinalEvaluationResponse,
    SubQuestionResult
)

from app.components.evaluation.services.scorer import (
    compute_scores_for_answer,
    build_bm25
)

from app.components.evaluation.services.feedback import (
    generate_feedback_for_answer,
    generate_overall_feedback
)

from app.components.evaluation.utils.helpers import (
    extract_main_question_id,
    select_best_main_questions
)


# ------------------------------------------------------------
# MAIN PIPELINE
# ------------------------------------------------------------
def run_evaluation(user_id: str, student_answers: dict, language: str, db: Session):

    print(f"\n\n================ EVALUATION STARTED =================")
    print(f"User ID: {user_id}")
    print(f"Total student answers received: {len(student_answers)}")
    print("----------------------------------------------------")

    # ------------------------------------------------------------
    # 1. Load saved teacher configuration
    # ------------------------------------------------------------
    syllabus = db.query(Syllabus).filter_by(user_id=user_id).first()
    questions = db.query(Question).filter_by(user_id=user_id).first()
    rubric = db.query(Rubric).filter_by(user_id=user_id).first()
    marks = db.query(Marks).filter_by(user_id=user_id).first()
    paper = db.query(PaperSettings).filter_by(user_id=user_id).first()

    if not syllabus or not questions or not rubric or not marks or not paper:
        print("ERROR: Missing teacher configuration")
        raise Exception("Teacher configuration incomplete. All uploads required.")

    syllabus_chunks = syllabus.syllabus_chunks
    question_dict = questions.questions
    marks_distribution = marks.marks_distribution

    rubric_weights = {
        "semantic_weight": rubric.semantic_weight,
        "coverage_weight": rubric.coverage_weight,
        "bm25_weight": rubric.bm25_weight
    }

    print("Loaded teacher data successfully.")
    print(f"Syllabus chunks: {len(syllabus_chunks)}")
    print(f"Questions loaded: {len(question_dict)}")
    print("----------------------------------------------------")

    # ------------------------------------------------------------
    # 2. Build BM25 once per evaluation
    # ------------------------------------------------------------
    print("Building BM25 index...")
    bm25 = build_bm25(syllabus_chunks)
    print("BM25 index ready.")
    print("----------------------------------------------------")

    # ------------------------------------------------------------
    # 3. Score all subquestions
    # ------------------------------------------------------------
    results = {}

    for qid, student_ans in student_answers.items():

        if qid not in question_dict:
            print(f"WARNING: Unknown question ID in student answers: {qid}, skipping...")
            continue

        print(f"\n--- Processing {qid} ---")
        print(f"Student answer length: {len(student_ans)} characters")

        question_text = question_dict[qid]

        # Compute semantic, coverage, bm25 scores
        score_info = compute_scores_for_answer(
            question_text=question_text,
            student_answer=student_ans,
            syllabus_chunks=syllabus_chunks,
            rubric=rubric_weights,
            marks_distribution=marks_distribution,
            qid=qid,
            bm25=bm25
        )

        print(f"Semantic Score: {score_info['semantic']:.3f}")
        print(f"Coverage Score: {score_info['coverage']:.3f}")
        print(f"BM25 Score:     {score_info['bm25']:.3f}")
        print(f"Allocated Marks: {score_info['allocated_marks']}")
        print(f"Final Score:     {score_info['final_score']:.2f}")

        # Generate subquestion feedback (Gemini)
        print(f"Generating Gemini feedback for {qid}...")
        feedback_text = generate_feedback_for_answer(
            qid=qid,
            student_answer=student_ans,
            score_details=score_info,
            language=language
        )
        print(f"Feedback completed for {qid}.")

        # Build structured result
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

    print("\nAll subquestions processed.")
    print("----------------------------------------------------")

    # ------------------------------------------------------------
    # 4. Group subquestions under main question
    # ------------------------------------------------------------
    grouped = {}
    for qid, res in results.items():
        main_id = extract_main_question_id(qid)
        grouped.setdefault(main_id, []).append(res)

    print(f"Main questions detected: {list(grouped.keys())}")
    print("----------------------------------------------------")

    # ------------------------------------------------------------
    # 5. Select the BEST required main questions
    # ------------------------------------------------------------
    selected_main_ids = select_best_main_questions(
        grouped,
        paper.required_main_questions
    )

    print(f"Selected main questions (best {paper.required_main_questions}): {selected_main_ids}")
    print("----------------------------------------------------")

    # ------------------------------------------------------------
    # 6. Compute final score
    # ------------------------------------------------------------
    final_score = 0

    for main_id in selected_main_ids:
        for sub_result in grouped[main_id]:
            final_score += sub_result.total_score

    final_score = min(final_score, paper.total_marks)
    print(f"Final Score: {final_score} / {paper.total_marks}")
    print("----------------------------------------------------")

    # ------------------------------------------------------------
    # 7. Overall feedback (Gemini)
    # ------------------------------------------------------------
    print("Generating overall feedback summary...")
    overall_feedback = generate_overall_feedback(
        results=results,
        final_score=final_score,
        max_score=paper.total_marks,
        language=language
    )
    print("Overall feedback ready.")
    print("----------------------------------------------------")

    # ------------------------------------------------------------
    # 8. Build final response
    # ------------------------------------------------------------
    print("Packaging final response...")
    print("================ EVALUATION COMPLETED =================\n")

    return FinalEvaluationResponse(
        results=results,
        selected_main_questions=selected_main_ids,
        final_score_obtained=final_score,
        final_score_total=paper.total_marks,
        overall_feedback=overall_feedback,
        per_question_feedback={qid: res.feedback for qid, res in results.items()}
    )
