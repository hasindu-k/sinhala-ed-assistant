#app/services/evaluation/grading_service.py

import logging
import re
import json
from uuid import UUID
from typing import Dict, Any, List
from decimal import Decimal

from rank_bm25 import BM25Okapi
from sentence_transformers import util
from sqlalchemy.orm import Session

from app.shared.models.answer_evaluation import (
    AnswerDocument,
    EvaluationResult,
    QuestionScore,
)
from app.shared.models.question_papers import Question, SubQuestion
from app.shared.models.session_resources import SessionResource
from app.shared.models.resource_file import ResourceFile
from app.shared.ai.embeddings import xlmr
from app.core.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


class GradingService:
    def __init__(self, db: Session):
        self.db = db
        self.gemini = GeminiClient()

    # ----------------------------------------------------------
    # MARK RESOLUTION
    # ----------------------------------------------------------
    def _resolve_max_marks(self, question):
        if hasattr(question, "max_marks") and question.max_marks:
            return int(question.max_marks)

        if isinstance(question, SubQuestion):
            parent = question.parent_question
            if parent and parent.sub_questions:
                explicit = [sq.max_marks for sq in parent.sub_questions if sq.max_marks]
                if explicit:
                    return int(question.max_marks or 1)
                return max(1, int(parent.max_marks) // len(parent.sub_questions))

        return 1
    # ----------------------------------------------------------
    # PUBLIC ENTRY
    # ----------------------------------------------------------
    def grade_answer_document(self, answer_doc_id: UUID, user_id: UUID):
        answer_doc = (
            self.db.query(AnswerDocument)
            .filter(AnswerDocument.id == answer_doc_id)
            .first()
        )
        if not answer_doc or not answer_doc.mapped_answers:
            raise ValueError("Answer document not ready for grading")

        from app.shared.models.evaluation_session import EvaluationSession
        eval_session = (
            self.db.query(EvaluationSession)
            .filter(EvaluationSession.id == answer_doc.evaluation_session_id)
            .first()
        )

        rubric_text = self._load_rubric_text(eval_session)
        syllabus_text = self._load_syllabus_text(eval_session)

        from app.services.evaluation.question_paper_service import QuestionPaperService
        qp_service = QuestionPaperService(self.db)

        question_papers = qp_service.get_question_papers_by_chat_session(
            eval_session.session_id
        )

        questions: List[Question] = []
        for qp in question_papers:
            questions.extend(qp_service.get_questions_by_paper(qp.id))

        # Check for existing evaluation result
        existing_result = (
            self.db.query(EvaluationResult)
            .filter(EvaluationResult.answer_document_id == answer_doc.id)
            .first()
        )

        if existing_result:
            logger.info(f"Updating existing evaluation result {existing_result.id}")
            # Clear existing scores
            self.db.query(QuestionScore).filter(
                QuestionScore.evaluation_result_id == existing_result.id
            ).delete()
            
            eval_result = existing_result
            eval_result.total_score = Decimal(0)
            eval_result.overall_feedback = "Grading in progress..."
        else:
            eval_result = EvaluationResult(
                answer_document_id=answer_doc.id,
                total_score=Decimal(0),
                overall_feedback="Grading in progress...",
            )
            self.db.add(eval_result)
        
        self.db.commit()
        self.db.refresh(eval_result)

        question_map = self._build_question_map(questions)
        total_score = Decimal(0)

        # ------------------------------------------------------
        # MAIN GRADING LOOP
        # ------------------------------------------------------
        for key, student_text in answer_doc.mapped_answers.items():
            target = self._find_matching_question(key, question_map)
            if not target:
                logger.error(f"UNRESOLVED mapping key: {key}")
                continue  

            max_marks = self._resolve_max_marks(target)

            reference_text = self._get_reference_context(
                target, syllabus_text, rubric_text
            )

            # Use Gemini for both scoring and feedback
            gemini_result = self._grade_with_gemini(
                student_text=student_text,
                reference_text=reference_text,
                question=target,
                max_marks=max_marks,
                q_number=key
            )
            
            awarded_marks = Decimal(str(gemini_result.get("score", 0))).quantize(Decimal("0.01"))
            feedback = gemini_result.get("feedback", "Feedback unavailable.")
            
            # Fallback if Gemini returns 0 but text similarity is high (safety net)
            # But user said scoring is "all the way wrong", so trust Gemini more.
            
            total_score += awarded_marks

            # ONLY store marks for sub-questions
            if isinstance(target, SubQuestion):
                qs = QuestionScore(
                    evaluation_result_id=eval_result.id,
                    sub_question_id=target.id,
                    awarded_marks=awarded_marks,
                    feedback=feedback,
                )

            elif isinstance(target, Question):
                qs = QuestionScore(
                    evaluation_result_id=eval_result.id,
                    question_id=target.id,
                    awarded_marks=awarded_marks,
                    feedback=feedback,
                )

            else:
                logger.error(f"Invalid target type for key {key}: {type(target)}")
                continue

            self.db.add(qs)

        self.db.flush()

        eval_result.total_score = sum(
            qs.awarded_marks for qs in self.db.query(QuestionScore)
            .filter(QuestionScore.evaluation_result_id == eval_result.id)
        )

        eval_result.overall_feedback = self._generate_overall_feedback(
            total_score, eval_result.id
        )

        self.db.commit()
        return eval_result

    # ----------------------------------------------------------
    # SCORING LOGIC (FIXED)
    # ----------------------------------------------------------
    def _score_answer(self, student_text: str, reference_text: str, max_marks: int) -> float:
        q_type = self._classify_question(max_marks)
        semantic = self._semantic_similarity(student_text, reference_text)

        # Short factual answers
        if q_type == "short":
            return 1.0 if semantic >= 0.70 else semantic

        # Structured answers
        if q_type == "structured":
            return 1.0 if semantic >= 0.65 else semantic * 0.9

        # Essay answers (EXAMINER STYLE)
        coverage, _ = self._calculate_coverage_score(
            student_text, reference_text, max_marks
        )

        return self._apply_marking_band(semantic, coverage)

    def _classify_question(self, max_marks: int) -> str:
        if max_marks <= 2:
            return "short"
        if max_marks <= 4:
            return "structured"
        return "essay"

    def _semantic_similarity(self, student_text: str, reference_text: str) -> float:
        if not reference_text:
            return 0.0
        emb1 = xlmr.encode(student_text, convert_to_tensor=True)
        emb2 = xlmr.encode(reference_text, convert_to_tensor=True)
        return max(0.0, min(1.0, util.cos_sim(emb1, emb2).item()))

    # ----------------------------------------------------------
    # MARKING BANDS (CRITICAL FIX)
    # ----------------------------------------------------------
    def _apply_marking_band(self, semantic: float, coverage: float) -> float:
        combined = (0.6 * semantic) + (0.4 * coverage)

        if combined >= 0.85:
            return 0.95   # Excellent
        if combined >= 0.75:
            return 0.85   # Very good
        if combined >= 0.65:
            return 0.70   # Good
        if combined >= 0.50:
            return 0.55   # Partial
        if combined >= 0.35:
            return 0.35   # Weak
        if combined >= 0.20:
            return 0.20   # Very weak

        return 0.0

    # ----------------------------------------------------------
    # CONTEXT & COVERAGE
    # ----------------------------------------------------------
    def _get_reference_context(self, question, syllabus_text: str, rubric_text: str) -> str:
        q_text = getattr(question, "question_text", "") or getattr(
            question, "sub_question_text", ""
        )
        source = syllabus_text or rubric_text
        if not source:
            return ""

        chunks = [c.strip() for c in source.split("\n\n") if c.strip()]
        if not chunks:
            chunks = [c.strip() for c in source.split("\n") if c.strip()]

        bm25 = BM25Okapi([c.split() for c in chunks])
        return bm25.get_top_n(q_text.split(), chunks, n=1)[0]

    def _calculate_coverage_score(self, student_text, reference_text, max_marks):
        if not reference_text:
            return 0.0, "No reference"

        sentences = re.split(r"(?<=[.!?])\s+", reference_text)
        sentences = [s for s in sentences if len(s.strip()) > 10]

        student_emb = xlmr.encode(student_text, convert_to_tensor=True)

        hits = 0
        for s in sentences:
            sim = util.cos_sim(
                student_emb, xlmr.encode(s, convert_to_tensor=True)
            ).item()
            if sim >= 0.55:
                hits += 1

        ratio = hits / max(1, len(sentences))
        return min(1.0, ratio), f"{hits}/{len(sentences)} concepts covered"

    # ----------------------------------------------------------
    # QUESTION MAPPING
    # ----------------------------------------------------------
    def _build_question_map(self, questions: List[Question]) -> Dict[str, Any]:
        q_map = {}
        for q in questions:
            q_num = str(q.question_number).lower().replace(".", "")
            q_map[q_num] = q
            q_map[str(q.id)] = q

            for sq in q.sub_questions or []:
                key = f"{q_num}{sq.label}".replace("(", "").replace(")", "")
                q_map[key] = sq
                q_map[str(sq.id)] = sq
        return q_map

    def _find_matching_question(self, key: str, q_map: Dict[str, Any]):
        norm = key.lower().replace(" ", "").replace(".", "").replace("(", "").replace(")", "")
        return q_map.get(key) or q_map.get(norm)

    # ----------------------------------------------------------
    # LOADERS
    # ----------------------------------------------------------
    def _load_rubric_text(self, eval_session):
        res = (
            self.db.query(SessionResource)
            .filter(
                SessionResource.session_id == eval_session.session_id,
                SessionResource.label == "rubric",
            )
            .first()
        )
        if res:
            rf = self.db.query(ResourceFile).filter(ResourceFile.id == res.resource_id).first()
            return rf.extracted_text if rf else ""
        return ""

    def _load_syllabus_text(self, eval_session):
        res = (
            self.db.query(SessionResource)
            .filter(
                SessionResource.session_id == eval_session.session_id,
                SessionResource.label == "syllabus",
            )
            .first()
        )
        if res:
            rf = self.db.query(ResourceFile).filter(ResourceFile.id == res.resource_id).first()
            return rf.extracted_text if rf else ""
        return ""

    # ----------------------------------------------------------
    # GEMINI FEEDBACK
    # ----------------------------------------------------------
    def _grade_with_gemini(
        self, student_text, reference_text, question, max_marks, q_number
    ) -> Dict[str, Any]:
        try:
            q_text = getattr(question, "question_text", "") or getattr(
                question, "sub_question_text", ""
            )
            
            # Try to get a human-readable number if possible
            display_number = q_number
            if hasattr(question, "question_number") and question.question_number:
                display_number = question.question_number
            elif hasattr(question, "label") and question.label:
                 # It's a subquestion, try to find parent
                 if hasattr(question, "question") and question.question and question.question.question_number:
                     display_number = f"{question.question.question_number}({question.label})"
                 else:
                     display_number = question.label

            prompt = f"""
You are an expert teacher grading a student's answer.
Question {display_number}: {q_text}
Max Marks: {max_marks}

Reference/Rubric:
{reference_text}

Student Answer:
{student_text}

Task:
1. Compare the student's answer with the reference.
2. Award marks based on accuracy and completeness.
3. Provide short, helpful feedback in Sinhala.

Output JSON ONLY:
{{
    "score": <float_marks_awarded>,
    "feedback": "<feedback_string>"
}}
"""
            response = self.gemini.generate_content(prompt).get("text", "")
            
            # Clean up response to ensure valid JSON
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            
            data = json.loads(cleaned_response.strip())
            
            # Ensure feedback has the question number prefix
            feedback_text = data.get("feedback", "")
            data["feedback"] = f"**Question {display_number}**\n\n{feedback_text}"
            
            return data
            
        except Exception as e:
            logger.error(f"Gemini grading failed for {q_number}: {e}")
            return {"score": 0.0, "feedback": f"**Question {q_number}**\nGrading unavailable."}

    def _generate_overall_feedback(self, total_score, result_id):
        try:
            prompt = f"""
Total Score: {total_score}
Give concise overall feedback in Sinhala.
"""
            return self.gemini.generate_content(prompt).get("text", "")
        except Exception:
            return f"Total Score: {total_score}"
