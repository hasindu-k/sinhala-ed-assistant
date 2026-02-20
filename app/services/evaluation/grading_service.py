#app/services/evaluation/grading_service.py

import logging
import re
import json
import time
from uuid import UUID
from typing import Dict, Any, List, Tuple
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
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
from app.shared.models.rubrics import Rubric, RubricCriterion

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
    def grade_answer_document(self, answer_doc_id: UUID, user_id: UUID, progress_callback=None):
        answer_doc = (
            self.db.query(AnswerDocument)
            .filter(AnswerDocument.id == answer_doc_id)
            .first()
        )
        if not answer_doc or not answer_doc.mapped_answers:
            raise ValueError("Answer document not ready for grading")

        if progress_callback:
            progress_callback("initializing_grading", "Preparing grading context...")

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

        # ---- HOIST LOOP-INVARIANT WORK ----
        # Fetch rubric weights once for the entire document (not per-question)
        rubric_weights = self._get_rubric_weights(eval_session)

        total_questions = len(answer_doc.mapped_answers)
        processed_count = 0

        if progress_callback:
            progress_callback("evaluating_answers", f"Scoring {total_questions} answers...")

        # -------------------------------------------------------
        # PHASE 1: Parallel system scoring (XLM-R — CPU-bound)
        # -------------------------------------------------------
        # Collect all scoring work items first
        score_inputs: List[Tuple] = []  # (key, student_text, target, max_marks, reference_text)
        for key, student_text in answer_doc.mapped_answers.items():
            target = self._find_matching_question(key, question_map)
            if not target:
                logger.error(f"UNRESOLVED mapping key: {key}")
                continue

            max_marks = self._resolve_max_marks(target)
            reference_text = self._get_reference_context(target, syllabus_text, rubric_text)
            score_inputs.append((key, student_text, target, max_marks, reference_text))

        # Run system scoring synchronously (XLM-R shares a single GPU/CPU process — not safe to parallelize)
        scored_items: List[Dict] = []
        for idx, (key, student_text, target, max_marks, reference_text) in enumerate(score_inputs):
            processed_count += 1
            if progress_callback:
                pct = int((processed_count / total_questions) * 70)  # scoring = 0-70%
                progress_callback("evaluating_answers", f"Scoring question {key}...", percent=pct)

            system_score_ratio = self._calculate_system_score(
                student_text=student_text,
                reference_text=reference_text,
                weights=rubric_weights
            )
            awarded_marks = Decimal(str(system_score_ratio * max_marks)).quantize(Decimal("0.01"))
            display_number = self._resolve_display_number(target, key)

            scored_items.append({
                "key": key,
                "student_text": student_text,
                "reference_text": reference_text,
                "target": target,
                "max_marks": max_marks,
                "awarded_marks": awarded_marks,
                "display_number": display_number,
            })

        # -------------------------------------------------------
        # PHASE 2: Parallel Gemini feedback (I/O-bound — safe to parallelize)
        # -------------------------------------------------------
        if progress_callback:
            progress_callback("generating_feedback", "Generating feedback in parallel...", percent=70)

        def _fetch_feedback(item: Dict) -> Tuple[str, str]:
            """Returns (key, feedback_text)"""
            feedback = self._get_feedback_from_gemini(
                student_text=item["student_text"],
                reference_text=item["reference_text"],
                question=item["target"],
                awarded_marks=float(item["awarded_marks"]),
                max_marks=item["max_marks"],
                display_number=item["display_number"],
            )
            return item["key"], feedback

        feedback_map: Dict[str, str] = {}
        max_workers = min(10, len(scored_items)) if scored_items else 1
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_fetch_feedback, item): item["key"] for item in scored_items}
            done_count = 0
            for future in as_completed(futures):
                key, feedback = future.result()
                feedback_map[key] = feedback
                done_count += 1
                if progress_callback:
                    pct = 70 + int((done_count / len(scored_items)) * 25)  # feedback = 70-95%
                    progress_callback("generating_feedback", f"Feedback done {done_count}/{len(scored_items)}...", percent=pct)

        # -------------------------------------------------------
        # PHASE 3: Persist QuestionScore rows
        # -------------------------------------------------------
        total_score = Decimal(0)
        for item in scored_items:
            key = item["key"]
            target = item["target"]
            awarded_marks = item["awarded_marks"]
            feedback = feedback_map.get(key, f"**Question {item['display_number']}**\n(Feedback unavailable)")

            total_score += awarded_marks

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

        if progress_callback:
            progress_callback("calculating_marks", "Calculating final score...", percent=96)

        eval_result.total_score = sum(
            qs.awarded_marks for qs in self.db.query(QuestionScore)
            .filter(QuestionScore.evaluation_result_id == eval_result.id)
        )

        if progress_callback:
            progress_callback("generating_feedback", "Generating overall feedback...", percent=98)

        eval_result.overall_feedback = self._generate_overall_feedback(
            total_score, eval_result.id
        )

        if progress_callback:
            progress_callback("preparing_report", "Finalizing report...", percent=99)

        self.db.commit()
        return eval_result

    # ----------------------------------------------------------
    # SCORING LOGIC
    # ----------------------------------------------------------
    def _score_answer(self, student_text: str, reference_text: str, max_marks: int) -> float:
        q_type = self._classify_question(max_marks)
        semantic = self._semantic_similarity(student_text, reference_text)

        if q_type == "short":
            return 1.0 if semantic >= 0.70 else semantic
        if q_type == "structured":
            return 1.0 if semantic >= 0.65 else semantic * 0.9

        coverage, _ = self._calculate_coverage_score(student_text, reference_text, max_marks)
        return self._apply_marking_band(semantic, coverage)

    def _classify_question(self, max_marks: int) -> str:
        if max_marks <= 2:
            return "short"
        if max_marks <= 4:
            return "structured"
        return "essay"

    def _semantic_similarity(self, student_text: str, reference_text: str) -> float:
        if not reference_text or not student_text:
            return 0.0
        emb1 = xlmr.encode(student_text, convert_to_tensor=True)
        emb2 = xlmr.encode(reference_text, convert_to_tensor=True)
        raw_sim = util.cos_sim(emb1, emb2).item()

        boosted = min(1.0, max(0.0, raw_sim * 1.2))

        if boosted > 0.60:
            return 0.75 + (boosted - 0.60) * (0.25 / 0.40)

        return boosted

    # ----------------------------------------------------------
    # MARKING BANDS
    # ----------------------------------------------------------
    def _apply_marking_band(self, semantic: float, coverage: float) -> float:
        combined = (0.6 * semantic) + (0.4 * coverage)

        if combined >= 0.85:
            return 0.95
        if combined >= 0.75:
            return 0.85
        if combined >= 0.65:
            return 0.70
        if combined >= 0.50:
            return 0.55
        if combined >= 0.35:
            return 0.35
        if combined >= 0.20:
            return 0.20

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
        top_chunks = bm25.get_top_n(q_text.split(), chunks, n=3)
        return "\n\n".join(top_chunks)

    def _calculate_coverage_score(self, student_text: str, reference_text: str, max_marks: int):
        """
        Optimized: batch-encodes all reference sentences in a single XLM-R forward pass
        instead of one pass per sentence.
        """
        if not reference_text:
            return 0.0, "No reference"

        sentences = re.split(r"(?<=[.!?])\s+", reference_text)
        sentences = [s for s in sentences if len(s.strip()) > 10]

        if not sentences:
            return 0.0, "No reference sentences"

        # Encode student text once
        student_emb = xlmr.encode(student_text, convert_to_tensor=True)

        # Batch-encode ALL reference sentences in one forward pass (major speedup)
        sentence_embs = xlmr.encode(sentences, batch_size=32, convert_to_tensor=True)

        # Cosine similarities in one matrix operation
        sims = util.cos_sim(student_emb, sentence_embs)[0]  # shape: (num_sentences,)

        hits = int((sims >= 0.45).sum().item())

        ratio = hits / max(1, len(sentences) * 0.7)
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
    # SYSTEM SCORING & RUBRIC WEIGHTS
    # ----------------------------------------------------------
    def _get_rubric_weights(self, eval_session) -> Dict[str, float]:
        """Fetch weights for semantic, coverage, and relevance from the session's rubric."""
        default_weights = {"semantic": 0.6, "coverage": 0.2, "relevance": 0.2}

        if not eval_session.rubric_id:
            logger.warning(f"No rubric_id for session {eval_session.id}, using default weights")
            return default_weights

        criteria = (
            self.db.query(RubricCriterion)
            .filter(RubricCriterion.rubric_id == eval_session.rubric_id)
            .all()
        )

        if not criteria:
            logger.warning(f"No criteria found for rubric {eval_session.rubric_id}, using defaults")
            return default_weights

        weights = {c.criterion.lower(): c.weight_percentage for c in criteria}

        for key in default_weights:
            if key not in weights:
                weights[key] = default_weights[key]

        return weights

    def _calculate_system_score(self, student_text: str, reference_text: str, weights: Dict[str, float]) -> float:
        """Calculate score based on rubrics, using XLM-R for semantic similarity."""
        if not reference_text or not student_text:
            return 0.0

        # 1. Semantic Score (XLM-R)
        semantic = self._semantic_similarity(student_text, reference_text)

        # 2. Coverage Score (uses batched XLM-R encoding)
        coverage, _ = self._calculate_coverage_score(student_text, reference_text, 1)

        # 3. Relevance Score (word overlap — fast)
        relevance = self._calculate_relevance_score(student_text, reference_text)

        total = (
            weights.get("semantic", 0.6) * semantic +
            weights.get("coverage", 0.2) * coverage +
            weights.get("relevance", 0.2) * relevance
        )

        return max(0.0, min(1.0, total))

    def _calculate_relevance_score(self, student_text: str, reference_text: str) -> float:
        """Calculate relevance using keyword recall with lenient filtering."""
        if not reference_text or not student_text:
            return 0.0

        def get_keywords(text):
            words = re.findall(r'\w+', text.lower())
            return set([w for w in words if len(w) > 3])

        student_words = get_keywords(student_text)
        ref_words = get_keywords(reference_text)

        if not ref_words:
            return 1.0

        overlap = len(student_words & ref_words)
        recall = overlap / (len(ref_words) * 0.5)

        return min(1.0, recall)

    def _resolve_display_number(self, question, q_number: str) -> str:
        """Resolve a human-readable question number."""
        if hasattr(question, "question_number") and question.question_number:
            return str(question.question_number)
        elif hasattr(question, "label") and question.label:
            if hasattr(question, "question") and question.question and question.question.question_number:
                return f"{question.question.question_number}({question.label})"
            else:
                return str(question.label)
        return q_number

    # ----------------------------------------------------------
    # GEMINI FEEDBACK
    # ----------------------------------------------------------
    def _get_feedback_from_gemini(
        self, student_text, reference_text, question, awarded_marks, max_marks, display_number
    ) -> str:
        try:
            q_text = getattr(question, "question_text", "") or getattr(
                question, "sub_question_text", ""
            )

            prompt = f"""
You are an expert teacher in Sri Lanka. A system has already graded a student's answer.
Question {display_number}: {q_text}
Max Marks: {max_marks}
System Awarded Marks: {awarded_marks}

Reference/Rubric:
{reference_text}

Student Answer:
{student_text}

Task:
Provide short, helpful feedback in Sinhala explaining why the student received {awarded_marks} out of {max_marks}.
Highlight what was good and what could be improved based on the reference.
Be encouraging but accurate.

Output ONLY the feedback text in Sinhala.
"""
            response = self.gemini.generate_content(prompt).get("text", "")
            feedback_text = response.strip()

            return f"**Question {display_number}**\n\n{feedback_text}"

        except Exception as e:
            logger.error(f"Gemini feedback failed for {display_number}: {e}")
            return f"**Question {display_number}**\n(Feedback unavailable. Score: {awarded_marks}/{max_marks})"

    def _grade_with_gemini(self, *args, **kwargs):
        """Deprecated: Use _get_feedback_from_gemini for hybrid flow."""
        pass

    def _generate_overall_feedback(self, total_score, result_id):
        try:
            prompt = f"""
Total Score: {total_score}
Give concise overall feedback in Sinhala.
"""
            return self.gemini.generate_content(prompt).get("text", "")
        except Exception:
            return f"Total Score: {total_score}"
