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
import re
from sqlalchemy.orm import Session

from app.repositories.evaluation.answer_evaluation_repository import AnswerEvaluationRepository


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

    def get_answer_document_by_session_and_resource(self, evaluation_session_id: UUID, resource_id: UUID):
        """Get answer document by session and resource ID."""
        return self.repository.get_answer_document_by_session_and_resource(evaluation_session_id, resource_id)

    def update_mapped_answers(self, answer_document_id: UUID, mapped_answers: Dict):
        """Update mapped answers for an answer document."""
        return self.repository.update_mapped_answers(answer_document_id, mapped_answers)
    
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
        mapped_answers: List[Dict],  # [{question_id, sub_question_id, student_answer, ...}]
        question_lookup: Dict,      # {sub_question_id: {question_type, correct_answer, max_marks, question_text, resource_ids, ...}}
        rubric_weights: Optional[Dict[str, float]] = None,  # e.g., {"semantic": 0.5, "coverage": 0.3, "bm25": 0.2}
        db=None,
        overall_feedback: Optional[str] = None
    ):
        """
        Evaluate all mapped answers using question type and rubric.
        mapped_answers: list of dicts with keys: sub_question_id, student_answer, etc.
        question_lookup: dict mapping sub_question_id to question info (type, correct_answer, max_marks, ...)
        db: SQLAlchemy session (required for hybrid retrieval)
        """
        from app.services.hybrid_retrieval_service import HybridRetrievalService
        from app.services.semantic_similarity_service import SemanticSimilarityService
        from app.services.embedding_service import EmbeddingService
        scores = []
        for ans in mapped_answers:
            sub_qid = ans.get("sub_question_id")
            student_answer = ans.get("student_answer", "")
            qinfo = question_lookup.get(sub_qid, {})
            qtype = (qinfo.get("question_type") or "essay").lower()
            correct = qinfo.get("correct_answer")
            max_marks = qinfo.get("max_marks", 1)
            question_text = qinfo.get("question_text", "")
            resource_ids = qinfo.get("resource_ids", [])
            feedback = ""
            awarded = 0
            if qtype in ["mcq", "short"]:
                # Case-insensitive, whitespace-trimmed match
                if correct and student_answer.strip().lower() == correct.strip().lower():
                    awarded = max_marks
                    feedback = f"Correct answer. ({awarded}/{max_marks})"
                else:
                    awarded = 0
                    feedback = f"Incorrect answer. ({awarded}/{max_marks})"
            else:
                # Essay/structured: real semantic/coverage/bm25 scoring
                sem_weight = rubric_weights.get("semantic", 0.5) if rubric_weights else 0.5
                cov_weight = rubric_weights.get("coverage", 0.3) if rubric_weights else 0.3
                bm_weight = rubric_weights.get("bm25", 0.2) if rubric_weights else 0.2
                sem_score = cov_score = bm_score = 0.0
                reference_text = ""
                if db and resource_ids and question_text:
                    hybrid_service = HybridRetrievalService(db)
                    embedding = EmbeddingService.embed(question_text)
                    hits = hybrid_service.retrieve(
                        resource_ids=resource_ids,
                        query=question_text,
                        query_embedding=embedding,
                        bm25_k=3,
                        final_k=3
                    )
                    reference_text = " ".join([h["content"] for h in hits if h.get("content")])
                    sem_score = SemanticSimilarityService.similarity(student_answer, reference_text)
                    student_words = set(student_answer.split())
                    ref_words = set(reference_text.split())
                    cov_score = len(student_words & ref_words) / len(ref_words) if ref_words else 0.0
                    bm_score = max([h.get("similarity", 0.0) for h in hits], default=0.0)
                avg_score = sem_score * sem_weight + cov_score * cov_weight + bm_score * bm_weight
                awarded = float(max_marks) * avg_score
                feedback = f"Essay/structured answer scored. ({awarded:.2f}/{max_marks}) (Sim: {sem_score:.2f}, Cov: {cov_score:.2f}, BM25: {bm_score:.2f})"
            scores.append({
                "sub_question_id": sub_qid,
                "awarded_marks": awarded,
                "feedback": feedback
            })
        total_score = sum(Decimal(str(score["awarded_marks"])) for score in scores)
        # Try to get total_marks from question_lookup (sum of all max_marks)
        total_marks = sum(Decimal(str(q.get("max_marks", 0))) for q in question_lookup.values()) if question_lookup else None
        percentage_score = float(total_score) / float(total_marks) * 100 if total_marks and total_marks > 0 else None
        # Compose feedback string
        score_str = f"{float(total_score):.0f}/{float(total_marks):.0f}" if total_marks else f"{float(total_score):.0f}"
        percent_str = f" ({percentage_score:.1f}/100)" if percentage_score is not None else ""
        full_feedback = f"Score: {score_str}{percent_str}. "
        if overall_feedback:
            full_feedback += overall_feedback
        eval_result = self.repository.create_evaluation_result(
            answer_document_id=answer_document_id,
            total_score=total_score,
            overall_feedback=full_feedback
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

        # Sort scores naturally by question number
        def sort_key(score):
            q_num = ""
            if score.question and score.question.question_number:
                q_num = score.question.question_number
            elif score.sub_question:
                parent_num = ""
                if score.sub_question.question and score.sub_question.question.question_number:
                    parent_num = score.sub_question.question.question_number
                q_num = f"{parent_num}{score.sub_question.label}"
            return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', str(q_num))]

        scores.sort(key=sort_key)

        # Calculate grade (A: 85-100, B: 70-84, C: 55-69, D: 40-54, F: <40)
        def calc_grade(score):
            if score is None:
                return None
            try:
                score = float(score)
            except Exception:
                return None
            if score >= 85:
                return "A"
            elif score >= 70:
                return "B"
            elif score >= 55:
                return "C"
            elif score >= 40:
                return "D"
            else:
                return "F"

        # Extract missed concepts and improvement points from question feedbacks
        missing_concepts = []
        improvement_points = []
        for score in scores:
            fb = score.feedback or ""
            # Missed concepts: look for phrases indicating missing points
            if any(kw in fb.lower() for kw in ["missing", "should mention", "need to mention", "not mentioned", "should include", "not included", "අඩංගු විය යුතුය", "සඳහන් කළ යුතුය", "පැහැදිලි කළ යුතුය"]):
                # Extract the sentence(s) mentioning missing concepts
                for sent in re.split(r'[.\n]', fb):
                    if any(kw in sent.lower() for kw in ["missing", "should mention", "need to mention", "not mentioned", "should include", "not included", "අඩංගු විය යුතුය", "සඳහන් කළ යුතුය", "පැහැදිලි කළ යුතුය"]):
                        missing_concepts.append(sent.strip())
            # Improvement points: look for writing/clarity suggestions
            if any(kw in fb.lower() for kw in ["improve", "clarify", "writing style", "description", "elaborate", "expand", "unclear", "not clear", "not detailed", "කෙටි", "විස්තර", "සවිස්තර"]):
                for sent in re.split(r'[.\n]', fb):
                    if any(kw in sent.lower() for kw in ["improve", "clarify", "writing style", "description", "elaborate", "expand", "unclear", "not clear", "not detailed", "කෙටි", "විස්තර", "සවිස්තර"]):
                        improvement_points.append(sent.strip())
        # Add generic suggestions if none found
        if not improvement_points:
            improvement_points.append("Improve writing style and concept explanation.")

        feedback_obj = {
            "overall_feedback": result.overall_feedback,
            "missing_concepts": missing_concepts,
            "improvement_points": improvement_points
        }

        return {
            "id": result.id,
            "answer_document_id": result.answer_document_id,
            "total_score": float(result.total_score) if result.total_score else None,
            "grade": calc_grade(result.total_score),
            "feedback": feedback_obj,
            "evaluated_at": result.evaluated_at,
            "question_feedbacks": [
                {
                    "id": score.id,
                    "evaluation_result_id": score.evaluation_result_id,
                    "question_id": score.question_id,
                    "sub_question_id": score.sub_question_id,
                    "awarded_marks": score.awarded_marks,
                    "feedback": score.feedback
                }
                for score in scores
            ]
        }