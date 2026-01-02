from typing import Dict, List
from decimal import Decimal
import re
from app.components.evaluation.temporary.temporary_schemas import (
    TemporaryEvaluationInput,
    TemporaryEvaluationOutput,
    StudentEvaluationOutput,
    PartScore,
    MainQuestionScore,
    SubQuestionScore,
)
import logging

logger = logging.getLogger(__name__)


class TemporaryEvaluationService:
    """Temporary service for evaluation with detailed question structure and multiple students."""

    def evaluate_with_plain_text(self, input_data: TemporaryEvaluationInput) -> TemporaryEvaluationOutput:
        """
        Mock evaluation for multiple students with detailed paper structure.
        """
        logger.info("Starting temporary evaluation for %d students", len(input_data.student_answers))

        evaluations = []
        for student_answer in input_data.student_answers:
            answered_questions = self._parse_answered_questions(student_answer.answers_text)
            student_eval = self._evaluate_student(input_data, student_answer, answered_questions)
            evaluations.append(student_eval)

        return TemporaryEvaluationOutput(evaluations=evaluations)

    def _parse_answered_questions(self, answers_text: str) -> List[str]:
        """Parse main question numbers from answers text using regex for numbering like '1.', '2.', etc."""
        # Match patterns like "1.", "2.", "(1)", "1)", etc.
        pattern = r'\b(\d+)\.|\(\s*(\d+)\s*\)|\b(\d+)\)'
        matches = re.findall(pattern, answers_text)
        # Flatten the tuples and get unique numbers
        numbers = set()
        for match in matches:
            for num in match:
                if num:
                    numbers.add(num)
        return sorted(list(numbers))

    def _evaluate_student(self, input_data: TemporaryEvaluationInput, student, answered: List[str]) -> StudentEvaluationOutput:
        semantic = input_data.rubric_scores.get("semantic", 0.5)
        coverage = input_data.rubric_scores.get("coverage", 0.5)
        bm25 = input_data.rubric_scores.get("bm25", 0.5)
        avg_score = (semantic + coverage + bm25) / 3

        part_scores = []
        total_awarded = Decimal(0)

        for part in input_data.paper_parts:
            part_eval = self._evaluate_part(part, answered, avg_score)
            part_scores.append(part_eval)
            total_awarded += part_eval.awarded_marks

        overall_feedback = f"Student {student.student_id}: Detected {len(answered)} answered questions. " \
                          f"Semantic: {semantic}, Coverage: {coverage}, BM25: {bm25}. " \
                          f"Performance: {'Excellent' if avg_score > 0.8 else 'Good' if avg_score > 0.6 else 'Needs Improvement'}."

        return StudentEvaluationOutput(
            student_id=student.student_id,
            total_score=total_awarded,
            overall_feedback=overall_feedback,
            part_scores=part_scores
        )

    def _evaluate_part(self, part, answered: List[str], avg_score: float) -> PartScore:
        main_scores = []
        part_total = Decimal(0)

        # Collect answered scores
        answered_scores = []
        for mq in part.main_questions:
            if mq.number in answered:
                mq_eval = self._evaluate_main_question(mq, avg_score)
                answered_scores.append(mq_eval)
            else:
                mq_total = sum(sq.marks for sq in mq.sub_questions)
                mq_eval = MainQuestionScore(
                    number=mq.number,
                    total_marks=mq_total,
                    awarded_marks=Decimal(0),
                    sub_scores=[]
                )
            main_scores.append(mq_eval)
            part_total += mq_eval.total_marks

        # If more than required, drop the lowest scored
        if len(answered_scores) > part.required_questions:
            # Sort by awarded_marks descending
            answered_scores.sort(key=lambda x: x.awarded_marks, reverse=True)
            # Keep top required, set others to 0
            for i in range(part.required_questions, len(answered_scores)):
                answered_scores[i].awarded_marks = Decimal(0)
                for sub in answered_scores[i].sub_scores:
                    sub.awarded_marks = Decimal(0)

        part_awarded = sum(mq.awarded_marks for mq in main_scores)

        return PartScore(
            name=part.name,
            total_marks=part_total,
            awarded_marks=part_awarded,
            main_scores=main_scores
        )

    def _evaluate_main_question(self, mq, avg_score: float) -> MainQuestionScore:
        sub_scores = []
        awarded = Decimal(0)
        total = Decimal(0)

        for sq in mq.sub_questions:
            sq_awarded = Decimal(float(sq.marks) * avg_score)
            sub_scores.append(SubQuestionScore(
                label=sq.label,
                awarded_marks=sq_awarded,
                feedback=f"Subquestion {sq.label}: {'Well done' if sq_awarded > sq.marks * 0.7 else 'Partial credit'}."
            ))
            awarded += sq_awarded
            total += sq.marks

        return MainQuestionScore(
            number=mq.number,
            total_marks=total,
            awarded_marks=awarded,
            sub_scores=sub_scores
        )