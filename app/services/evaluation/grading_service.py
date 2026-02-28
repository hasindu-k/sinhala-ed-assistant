#app/services/evaluation/grading_service.py

import logging
import re
import json
import time
from uuid import UUID
from typing import Dict, Any, List, Tuple, Optional, Callable
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import torch
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
from app.shared.models.evaluation_session import EvaluationSession
from app.shared.models.resource_file import ResourceFile
from app.shared.models.rubrics import Rubric, RubricCriterion
from app.shared.ai.embeddings import xlmr, ml_semaphore
from app.core.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


class GradingService:
    def __init__(self, db: Session):
        self.db = db
        self.gemini = GeminiClient()
        self._sentence_cache = {} # Map sentence string -> embedding tensor


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
    def grade_answer_document(
        self,
        answer_doc_id: UUID,
        user_id: UUID,
        eval_session_id: UUID,
        syllabus_text: str,
        rubric_text: str,
        question_map: Dict,
        progress_callback: Optional[Callable[[str, str, Optional[int]], None]] = None,
        include_feedback: bool = True,
    ) -> EvaluationResult:
        answer_doc = (
            self.db.query(AnswerDocument)
            .filter(AnswerDocument.id == answer_doc_id)
            .first()
        )
        if not answer_doc or not answer_doc.mapped_answers:
            raise ValueError("Answer document not ready for grading")

        if progress_callback:
            progress_callback("initializing_grading", "Preparing grading context...")

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

        # ---- HOIST LOOP-INVARIANT WORK ----
        # Fetch rubric weights once for the entire document (not per-question)
        eval_session = self.db.query(EvaluationSession).filter(EvaluationSession.id == eval_session_id).first()
        rubric_weights = self._get_rubric_weights(eval_session)

        total_questions = len(answer_doc.mapped_answers)
        processed_count = 0

        if progress_callback:
            progress_callback("evaluating_answers", f"Scoring {total_questions} answers...")

        # -------------------------------------------------------
        # PHASE 1: System scoring (XLM-R — CPU-bound)
        # -------------------------------------------------------
        # 1.0 Gather all work items
        # -------------------------------------------------------
        score_inputs: List[Tuple] = []  # (key, student_text, target, max_marks, reference_text)
        for key, student_text in answer_doc.mapped_answers.items():
            target = self._find_matching_question(key, question_map)
            if not target:
                logger.error(f"UNRESOLVED mapping key: {key}")
                continue

            max_marks = self._resolve_max_marks(target)
            reference_text = self._get_reference_context(target, syllabus_text, rubric_text)
            score_inputs.append((key, student_text, target, max_marks, reference_text))

        # 1.1 Collect and Batch Encode all texts for the document
        # -------------------------------------------------------
        all_student_texts = [item[1] for item in score_inputs]
        all_ref_texts = list(set([item[4] for item in score_inputs if item[4]]))
        
        if progress_callback:
            progress_callback("evaluating_answers", "Batch encoding document content...", percent=5)

        with ml_semaphore:
            # Batch encode student answers
            student_embs = xlmr.encode(all_student_texts, batch_size=32, convert_to_tensor=True) if all_student_texts else []
            # Batch encode deduplicated reference contexts
            ref_embs_list = xlmr.encode(all_ref_texts, batch_size=32, convert_to_tensor=True) if all_ref_texts else []
        
        # Maps for quick lookup: text -> embedding tensor
        student_emb_map = {text: student_embs[i] for i, text in enumerate(all_student_texts)}
        ref_emb_map = {text: ref_embs_list[i] for i, text in enumerate(all_ref_texts)}

        scored_items: List[Dict] = []
        seen_question_ids = set() # To prevent duplicates in the final result

        for key, student_text in answer_doc.mapped_answers.items():
            target = self._find_matching_question(key, question_map)
            if not target:
                continue

            # Skip if we already graded this specific question/sub-question entry
            # (prevents same question appearing twice if mapped by both ID and Label)
            target_id = getattr(target, 'id', None)
            if target_id in seen_question_ids:
                logger.warning(f"Skipping duplicate mapping for question: {key}")
                continue
            seen_question_ids.add(target_id)

            max_marks = self._resolve_max_marks(target)
            reference_text = self._get_reference_context(target, syllabus_text, rubric_text)
            
            processed_count += 1
            if progress_callback:
                pct = 5 + int((processed_count / total_questions) * 65)  # scoring = 5-70%
                progress_callback("evaluating_answers", f"Scoring question {key}...", percent=pct)

            # Pass cached embeddings to avoid re-encoding
            s_emb = student_emb_map.get(student_text)
            r_emb = ref_emb_map.get(reference_text)

            system_score_ratio = self._calculate_system_score(
                student_text=student_text,
                reference_text=reference_text,
                weights=rubric_weights,
                max_marks=max_marks,
                student_emb=s_emb,
                reference_emb=r_emb
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
                "student_emb": s_emb # Pass for coverage scoring
            })


        # -------------------------------------------------------
        # PHASE 2: Batch Gemini feedback & relevance validation
        # -------------------------------------------------------
        eval_data_map: Dict[str, Dict] = {}
        if include_feedback:
            if progress_callback:
                progress_callback("generating_feedback", "Generating feedback and validating relevance...", percent=70)

            eval_data_map = self._get_batch_feedback_from_gemini(scored_items)

            if progress_callback:
                progress_callback("generating_feedback", "Feedback batch completed.", percent=95)
        else:
            if progress_callback:
                progress_callback("generating_feedback", "Skipping feedback for now (scoring only).", percent=95)

        # -------------------------------------------------------
        # PHASE 3: Persist QuestionScore rows
        # -------------------------------------------------------
        total_score = Decimal(0)
        for item in scored_items:
            key = item["key"]
            target = item["target"]
            awarded_marks = item["awarded_marks"]
            
            # Apply Gemini validation multiplier
            gemini_data = eval_data_map.get(key, {})
            multiplier = Decimal(str(gemini_data.get("relevance_multiplier", 1.0)))
            awarded_marks = (awarded_marks * multiplier).quantize(Decimal("0.01"))
            
            feedback = gemini_data.get("feedback")  # May be None if include_feedback=False

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

        if include_feedback:
            if progress_callback:
                progress_callback("generating_feedback", "Generating overall feedback...", percent=98)

            eval_result.overall_feedback = self._generate_overall_feedback(
                total_score, eval_result.id
            )

        if progress_callback:
            progress_callback("preparing_report", "Finalizing report...", percent=99)

        self.db.commit()
        return eval_result

    def generate_feedback_for_result(self, answer_doc_id: UUID, user_id: UUID) -> Optional[EvaluationResult]:
        """
        Generate Gemini feedback for an existing evaluation result.
        """
        # 1. Fetch existing result
        result = self.db.query(EvaluationResult).filter(EvaluationResult.answer_document_id == answer_doc_id).first()
        if not result:
            logger.error(f"Cannot generate feedback: No evaluation result for {answer_doc_id}")
            return None

        # 2. Fetch answer document and session details to rebuild context
        answer_doc = (
            self.db.query(AnswerDocument)
            .filter(AnswerDocument.id == answer_doc_id)
            .first()
        )
        if not answer_doc:
            return None

        eval_session = (
            self.db.query(EvaluationSession)
            .filter(EvaluationSession.id == answer_doc.evaluation_session_id)
            .first()
        )
        if not eval_session:
            return None

        # 3. Get context (Rubric, Question Map)
        from app.services.evaluation.evaluation_workflow_service import EvaluationWorkflowService
        workflow = EvaluationWorkflowService(self.db)
        
        syllabus_text, rubric_text, questions = workflow._get_evaluation_context(eval_session.id)
        question_map = workflow._build_question_map_helper(questions)

        # 4. Fetch existing scores to get display numbers and texts
        scores = self.db.query(QuestionScore).filter(QuestionScore.evaluation_result_id == result.id).all()
        
        # Reconstruct scored_items for the batch feedback method
        scored_items = []
        for qs in scores:
            target = None
            if qs.sub_question_id:
                target = qs.sub_question
            elif qs.question_id:
                target = qs.question
            
            if not target:
                continue

            # Find the key in mapped_answers
            key = None
            for k, val in answer_doc.mapped_answers.items():
                if str(target.id) in str(val) or k == str(target.id): 
                    key = k
                    break
            
            if not key:
                key = str(target.id)

            display_number = self._resolve_display_number(target, key)
            reference_text = self._get_reference_context(target, syllabus_text, rubric_text)
            
            scored_items.append({
                "key": key,
                "student_text": answer_doc.mapped_answers.get(key, ""),
                "reference_text": reference_text,
                "target": target,
                "max_marks": self._resolve_max_marks(target),
                "awarded_marks": qs.awarded_marks,
                "display_number": display_number,
                "db_score_obj": qs
            })

        if not scored_items:
            return result

        # 5. Generate Batch & Overall Feedback Concurrently
        logger.info(f"Generating on-demand batch & overall feedback for result {result.id}")
        feedback_map = {}
        overall_feedback = ""

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_batch = executor.submit(self._get_batch_feedback_from_gemini, scored_items)
            future_overall = executor.submit(self._generate_overall_feedback, result.total_score, result.id)
            
            try:
                eval_data_map = future_batch.result()
            except Exception as e:
                logger.error(f"Batch feedback generation failed: {e}")
                eval_data_map = {}
                
            try:
                overall_feedback = future_overall.result()
            except Exception as e:
                logger.error(f"Overall feedback generation failed: {e}")
                overall_feedback = f"Total Score: {result.total_score}"

        # 6. Update individual scores
        for item in scored_items:
            qs = item["db_score_obj"]
            gemini_data = eval_data_map.get(item["key"], {})
            
            multiplier = Decimal(str(gemini_data.get("relevance_multiplier", 1.0)))
            new_score = (item["awarded_marks"] * multiplier).quantize(Decimal("0.01"))
            qs.awarded_marks = min(Decimal(str(item["max_marks"])), max(Decimal("0"), new_score))
            
            feedback = gemini_data.get("feedback")
            if feedback:
                qs.feedback = feedback

        # 7. Generate overall feedback
        result.overall_feedback = overall_feedback
        
        self.db.commit()
        return result

    # ----------------------------------------------------------
    # SCORING HELPERS
    # ----------------------------------------------------------

    def _semantic_similarity(self, student_text: str, reference_text: str, student_emb=None, reference_emb=None) -> float:
        if not reference_text or not student_text:
            return 0.0
            
        # Use cached embeddings if provided
        emb1 = student_emb if student_emb is not None else xlmr.encode(student_text, convert_to_tensor=True)
        emb2 = reference_emb if reference_emb is not None else xlmr.encode(reference_text, convert_to_tensor=True)
        
        raw_sim = util.cos_sim(emb1, emb2).item()

        # Semantic boost for Sinhala (more aggressive 1.4 for short-answer accuracy)
        boosted = min(1.0, max(0.0, raw_sim * 1.4))

        if boosted > 0.50: 
            return 0.50 + (boosted - 0.50) * (0.50 / 0.50)

        return boosted


    # ----------------------------------------------------------
    # MARKING BANDS
    # ----------------------------------------------------------
    def _apply_marking_band(self, semantic: float, coverage: float) -> float:
        combined = (0.6 * semantic) + (0.4 * coverage)

        # Stricter, more proportional bands to avoid inflating poor answers
        if combined >= 0.85:
            return 0.90 + (combined - 0.85) * (0.10 / 0.15)  # 0.85 -> 0.90, 1.0 -> 1.0
        if combined >= 0.70:
            return 0.75 + (combined - 0.70) * (0.15 / 0.15)  # 0.70 -> 0.75, 0.85 -> 0.90
        if combined >= 0.55:
            return 0.60 + (combined - 0.55) * (0.15 / 0.15)  # 0.55 -> 0.60, 0.70 -> 0.75
        if combined >= 0.40:
            return 0.45 + (combined - 0.40) * (0.15 / 0.15)  # 0.40 -> 0.45, 0.55 -> 0.60

        return combined

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
        # Increase n from 3 to 5 to get more context
        top_chunks = bm25.get_top_n(q_text.split(), chunks, n=5)
        return "\n\n".join(top_chunks)

    def _calculate_coverage_score(self, student_text: str, reference_text: str, max_marks: int, student_emb=None):
        """
        Optimized: batch-encodes all reference sentences in a single XLM-R forward pass
        instead of one pass per sentence.
        """
        if not reference_text:
            return 0.0, "No reference"

        sentences = re.split(r"(?<=[.!?])\s+", reference_text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        if not sentences:
            return 0.0, "No reference sentences"

        # Use cached student embedding if provided
        s_emb = student_emb if student_emb is not None else xlmr.encode(student_text, convert_to_tensor=True)

        # -------------------------------------------------------
        # Identify sentences not yet in the cache
        # -------------------------------------------------------
        missing_sentences = [s for s in sentences if s not in self._sentence_cache]
        
        if missing_sentences:
            with ml_semaphore:
                # Batch encode only the new sentences
                new_embs = xlmr.encode(missing_sentences, batch_size=32, convert_to_tensor=True)
                for i, s in enumerate(missing_sentences):
                    self._sentence_cache[s] = new_embs[i]

        # Assemble the full matrix of embeddings for THIS question
        sentence_embs = torch.stack([self._sentence_cache[s] for s in sentences])

        # Cosine similarities in one matrix operation
        sims = util.cos_sim(s_emb, sentence_embs)[0]  # shape: (num_sentences,)

        # Stricter hit threshold (0.45) for Sinhala concept matching
        hits = int((sims >= 0.45).sum().item())

        # Stricter divisor (0.75 instead of 0.5)
        ratio = hits / max(1, len(sentences) * 0.75)
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
    # These methods are now in AnswerEvaluationService and are no longer needed here.
    
    def _build_question_map(self, questions: List[Question]) -> Dict[str, Any]:
        """Backward compatibility for building question map."""
        q_map = {}
        for q in questions:
            q_num = str(q.question_number).lower().replace(".", "")
            # Composite keys for AI mapping strings
            q_map[q_num] = q
            # Direct ID keys for precise mapping
            q_map[str(q.id)] = q

            for sq in getattr(q, "sub_questions", []) or []:
                key = f"{q_num}{sq.label}".replace("(", "").replace(")", "")
                q_map[key] = sq
                q_map[str(sq.id)] = sq
        return q_map

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

    def _calculate_system_score(self, student_text: str, reference_text: str, weights: Dict[str, float], max_marks: int = 1, student_emb=None, reference_emb=None) -> float:
        """Calculate score using discrete snapping for short answers and weighted metrics for essays."""
        if not reference_text or not student_text:
            return 0.0

        # 1. Semantic Score (XLM-R)
        semantic = self._semantic_similarity(student_text, reference_text, student_emb, reference_emb)

        # Handle Short Factual Answers (Paper I Style: <= 2 marks)
        if max_marks <= 2:
            # Discrete snapping for short factual items
            # Sinhala embeddings are naturally lower: use more lenient thresholds
            # If meaning is mostly correct (>0.50), give full marks. If partially correct (>0.35), give half.
            if semantic >= 0.50: return 1.0
            if semantic >= 0.35: return 0.5
            return semantic # Raw score for very low matches

        # Handle Essay/Structured Answers (Paper II Style: > 2 marks)
        # 2. Coverage Score (normalized for concise correct answers)
        coverage, _ = self._calculate_coverage_score(student_text, reference_text, max_marks, student_emb)

        # 3. Relevance Score
        relevance = self._calculate_relevance_score(student_text, reference_text)

        # 4. Weighted Integration (Meaning-First: 75% Semantic)
        # Shift weights to prioritize semantic meaning over word-count metrics
        s_w = 0.75
        c_w = 0.125
        r_w = 0.125
        
        total = (s_w * semantic) + (c_w * coverage) + (r_w * relevance)

        # Apply marking bands for distribution smoothing
        banded_score = self._apply_marking_band(semantic, coverage)
        
        if semantic >= 0.85:
            final_score = max(banded_score, total, 0.85)
        elif semantic >= 0.60:
            final_score = (banded_score * 0.60) + (total * 0.40)
        else:
            final_score = (banded_score * 0.20) + (total * 0.80)

        return max(0.0, min(1.0, final_score))


    def _calculate_relevance_score(self, student_text: str, reference_text: str) -> float:
        """Calculate relevance using keyword recall with lenient filtering."""
        if not reference_text or not student_text:
            return 0.0

        def get_keywords(text):
            words = re.findall(r'\w+', text.lower())
            # For Sinhala, words slightly longer than 2 characters often carry meaning
            return set([w for w in words if len(w) > 2])

        student_words = get_keywords(student_text)
        ref_words = get_keywords(reference_text)

        if not ref_words:
            return 1.0

        overlap = len(student_words & ref_words)
        # Stricter recall divisor (0.7)
        recall = overlap / max(1, len(ref_words) * 0.7)

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
    def _get_batch_feedback_from_gemini(self, items: List[Dict]) -> Dict[str, Dict]:
        """
        Request feedback for multiple questions in smaller concurrent batches.
        Returns map of key -> {feedback: str, relevance_multiplier: float}.
        """
        if not items:
            return {}

        base_prompt = """
You are an expert teacher in Sri Lanka. A system has already graded several student answers based on meaning and keyword coverage.
Provide short, helpful feedback in Sinhala for each question, explaining why the student gained those marks, and what could be improved based on the reference.

**CRITICAL INSTRUCTION:**
1. You MUST also validate the core meaning and relevance of the answer. Provide a `relevance_multiplier`:
   - `1.0` if the student's answer is highly relevant and the core meaning answers the question properly. Note: Short correct answers (e.g. naming 2 items) MUST get `1.0`.
   - `0.5` if the answer is partially relevant but flawed or incomplete.
   - `0.0` if the answer is complete gibberish, hallucinates, or does not address the question at all.
2. If the student missed certain concepts, you MUST explicitly state the missing points using phrases like "අඩංගු විය යුතුය", "මඟ හැරී ඇත", "සඳහන් කළ යුතුය", or "පැහැදිලි කළ යුතුය". The system relies on these keywords to extract 'Missing Concepts' and 'Improvement Points'. Be encouraging but accurate.
3. Return the results as a JSON object where names are the question keys, and values are objects containing strictly 'feedback' and 'relevance_multiplier'.

Example format:
{
  "1": { "feedback": "මාතෘකාවට අදාළයි. නමුත් [X] අඩංගු විය යුතුය...", "relevance_multiplier": 1.0 },
  "2අ": { "feedback": "මෙම පිළිතුර ප්රශ්නයට අදාළ නැත...", "relevance_multiplier": 0.0 }
}

Questions to evaluate:
"""
        def process_chunk(chunk: List[Dict]) -> Dict[str, Dict]:
            chunk_prompt = base_prompt
            for item in chunk:
                q_text = getattr(item["target"], "question_text", "") or getattr(
                    item["target"], "sub_question_text", ""
                )
                chunk_prompt += f"\n--- Key: {item['key']} ---\n"
                chunk_prompt += f"Question Number: {item['display_number']}\n"
                chunk_prompt += f"Question: {q_text}\n"
                chunk_prompt += f"Target Marks: {item['max_marks']}\n"
                chunk_prompt += f"System Score Estimate: {item['awarded_marks']} (Ensure 'relevance_multiplier' validates this)\n"
                chunk_prompt += f"Student Answer: {item['student_text']}\n"
                chunk_prompt += f"Reference: {item['reference_text']}\n"
            
            try:
                response_json = self.gemini.generate_content(chunk_prompt, json_mode=True).get("text", "{}")
                try:
                    clean_json = re.sub(r'^```json\s*|\s*```$', '', response_json.strip(), flags=re.MULTILINE)
                    return json.loads(clean_json)
                except Exception as e:
                    logger.error(f"Failed to parse batched feedback JSON: {e}. Raw: {response_json}")
                    return {}
            except Exception as e:
                logger.error(f"Batch Gemini feedback failed: {e}")
                return {}

        batch_size = 5
        chunks = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
        
        evaluation_data = {}
        with ThreadPoolExecutor(max_workers=min(len(chunks), 4)) as executor:
            future_to_chunk = {executor.submit(process_chunk, chunk): chunk for chunk in chunks}
            for future in as_completed(future_to_chunk):
                try:
                    result = future.result()
                    if result:
                        evaluation_data.update(result)
                except Exception as exc:
                    logger.error(f"Chunk processing generated an exception: {exc}")

        # Wrap feedback with question identifiers, keep multiplier isolated
        final_map = {}
        for item in items:
            key = item["key"]
            eval_result = evaluation_data.get(key, {})
            multiplier = eval_result.get("relevance_multiplier", 1.0)
            raw_feedback = eval_result.get("feedback", "(ප්‍රතිපෝෂණ ලබා ගත නොහැක)")
            
            final_map[key] = {
                "relevance_multiplier": multiplier,
                "feedback": f"**ප්‍රශ්නය {item['display_number']}**\n\n{raw_feedback}"
            }
        
        return final_map

    def _generate_overall_feedback(self, total_score, result_id):
        try:
            prompt = f"""
Total Score: {total_score}
Give concise overall feedback in Sinhala.
"""
            return self.gemini.generate_content(prompt).get("text", "")
        except Exception:
            return f"Total Score: {total_score}"
