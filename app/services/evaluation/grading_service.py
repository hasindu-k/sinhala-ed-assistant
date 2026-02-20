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
    def grade_answer_document(self, answer_doc_id: UUID, user_id: UUID, progress_callback=None, shared_cache=None):
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
        total_questions = len(answer_doc.mapped_answers)
        processed_count = 0

        if progress_callback:
            progress_callback("evaluating_answers", f"Grading {total_questions} answers...")

        from concurrent.futures import ThreadPoolExecutor, as_completed

        # --- PRE-PROCESS QUESTIONS ---
        grading_tasks = []
        for key, student_text in answer_doc.mapped_answers.items():
            target = self._find_matching_question(key, question_map)
            if not target:
                logger.error(f"UNRESOLVED mapping key: {key}")
                continue  

            max_marks = self._resolve_max_marks(target)
            reference_text = self._get_reference_context(target, syllabus_text, rubric_text)
            rubric_weights = self._get_rubric_weights(eval_session)
            display_number = self._resolve_display_number(target, key)
            
            grading_tasks.append({
                "key": key,
                "target": target,
                "student_text": student_text,
                "reference_text": reference_text,
                "max_marks": max_marks,
                "weights": rubric_weights,
                "display_number": display_number
            })

        # --- BATCH SCORING ---
        if progress_callback:
            progress_callback("calculating_marks", f"Batch scoring {len(grading_tasks)} answers...")

        # Optimize: Batch encode all student answers at once
        student_texts = [t["student_text"] for t in grading_tasks]
        if student_texts:
            logger.info(f"Batch encoding {len(student_texts)} student answers...")
            student_embeddings = xlmr.encode(student_texts, convert_to_tensor=True)
            for i, task in enumerate(grading_tasks):
                task["student_embedding"] = student_embeddings[i]

        for task in grading_tasks:
            # Pass shared_cache and pre-computed student embedding
            system_score_ratio = self._calculate_system_score(
                student_text=task["student_text"],
                reference_text=task["reference_text"],
                weights=task["weights"],
                shared_cache=shared_cache,
                question_id=str(task["target"].id),
                student_emb=task.get("student_embedding")
            )
            task["awarded_marks"] = Decimal(str(system_score_ratio * task["max_marks"])).quantize(Decimal("0.01"))

        # --- PARALLEL FEEDBACK ---
        if progress_callback:
            progress_callback("generating_feedback", "Generating feedback concurrently...")

        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_task = {
                executor.submit(
                    self._get_feedback_from_gemini,
                    student_text=t["student_text"],
                    reference_text=t["reference_text"],
                    question=t["target"],
                    awarded_marks=float(t["awarded_marks"]),
                    max_marks=t["max_marks"],
                    display_number=t["display_number"]
                ): t for t in grading_tasks
            }

            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    task["feedback"] = future.result()
                except Exception as e:
                    logger.error(f"Feedback task failed for {task['display_number']}: {e}")
                    task["feedback"] = f"**Question {task['display_number']}**\n(Feedback error: {e})"

        # --- SAVE RESULTS ---
        total_score = Decimal(0)
        for task in grading_tasks:
            awarded_marks = task["awarded_marks"]
            feedback = task["feedback"]
            target = task["target"]
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
                continue
            self.db.add(qs)

        self.db.flush()

        if progress_callback:
            progress_callback("calculating_marks", "Calculating final score...")

        eval_result.total_score = sum(
            qs.awarded_marks for qs in self.db.query(QuestionScore)
            .filter(QuestionScore.evaluation_result_id == eval_result.id)
        )

        if progress_callback:
            progress_callback("generating_feedback", "Generating overall feedback...")

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

    def _semantic_similarity(self, student_text: str, reference_text: str, student_emb=None, reference_emb=None) -> float:
        if not reference_text or not student_text:
            return 0.0
        
        emb1 = student_emb if student_emb is not None else xlmr.encode(student_text, convert_to_tensor=True)
        emb2 = reference_emb if reference_emb is not None else xlmr.encode(reference_text, convert_to_tensor=True)
        
        raw_sim = util.cos_sim(emb1, emb2).item()
        
        # Apply 1.2x boost and clamp
        boosted = min(1.0, max(0.0, raw_sim * 1.2))
        
        # Nonlinear mapping for human-like grading
        # (e.g., 0.65 raw -> 0.8+ score)
        if boosted > 0.60:
            # Scale 0.6 -> 1.0 range into 0.75 -> 1.0 range
            return 0.75 + (boosted - 0.60) * (0.25 / 0.40)
        
        return boosted

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
        # Retrieve top 3 chunks for richer context
        top_chunks = bm25.get_top_n(q_text.split(), chunks, n=3)
        return "\n\n".join(top_chunks)

    def _calculate_coverage_score(self, student_text, reference_text, max_marks, student_emb=None, ref_sentences_with_emb=None):
        if not reference_text:
            return 0.0, "No reference"

        if student_emb is None:
            student_emb = xlmr.encode(student_text, convert_to_tensor=True)

        if ref_sentences_with_emb is not None:
            sentences_with_emb = ref_sentences_with_emb
        else:
            sentences = re.split(r"(?<=[.!?])\s+", reference_text)
            sentences = [s for s in sentences if len(s.strip()) > 10]
            sentences_with_emb = [(s, xlmr.encode(s, convert_to_tensor=True)) for s in sentences]

        if not sentences_with_emb:
            return 1.0, "Full coverage (Short reference)"

        hits = 0
        for s, s_emb in sentences_with_emb:
            sim = util.cos_sim(student_emb, s_emb).item()
            # Lower threshold for Sinhala linguistic variation
            if sim >= 0.45:
                hits += 1

        # Use 70% threshold for full coverage marks
        ratio = hits / max(1, len(sentences_with_emb) * 0.7)
        return min(1.0, ratio), f"{hits}/{len(sentences_with_emb)} concepts covered"

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
        
        # Ensure all key criteria exist
        for key in default_weights:
            if key not in weights:
                weights[key] = default_weights[key]
                
        return weights

    def _calculate_system_score(self, student_text: str, reference_text: str, weights: Dict[str, float], shared_cache=None, question_id=None, student_emb=None) -> float:
        """Calculate score based on rubrics, using XLM-R for semantic similarity."""
        if not reference_text or not student_text:
            return 0.0
            
        # 1. Semantic Score (XLM-R)
        ref_emb = None
        ref_sentences_with_emb = None
        
        if shared_cache and question_id:
            ref_emb = shared_cache.get("reference_embeddings", {}).get(question_id)
            ref_sentences_with_emb = shared_cache.get("reference_sentences", {}).get(question_id)

        semantic = self._semantic_similarity(student_text, reference_text, student_emb=student_emb, reference_emb=ref_emb)
        
        # 2. Coverage Score
        coverage, _ = self._calculate_coverage_score(
            student_text, reference_text, 1, student_emb=student_emb, ref_sentences_with_emb=ref_sentences_with_emb
        ) 
        
        # 3. Relevance Score (Word overlap / alignment)
        relevance = self._calculate_relevance_score(student_text, reference_text)
        
        # Combined Score
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
            # Simple keyword filter: length > 3 characters (avoid particles)
            words = re.findall(r'\w+', text.lower())
            return set([w for w in words if len(w) > 3])
            
        student_words = get_keywords(student_text)
        ref_words = get_keywords(reference_text)
        
        if not ref_words:
            return 1.0 # If no keywords in ref, assume relevant
            
        overlap = len(student_words & ref_words)
        # Recall: how many ref keywords matched?
        # Target: matching 50% of reference keywords is usually 100% relevant
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
