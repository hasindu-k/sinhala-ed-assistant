#app/services/evaluation/grading_service.py

import logging
import re
import json
import time
from math import floor
from uuid import UUID
from typing import Dict, Any, List, Tuple, Optional, Callable
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import torch
from rank_bm25 import BM25Okapi
from sentence_transformers import util
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.shared.models.answer_evaluation import (
    AnswerDocument,
    EvaluationResult,
    QuestionScore,
)
from app.shared.models.question_papers import Question, SubQuestion
from app.shared.models.session_resources import SessionResource
from app.shared.models.evaluation_session import EvaluationSession, PaperConfig
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

        # Check for existing evaluation result (Upsert pattern to prevent race conditions)
        eval_result = (
            self.db.query(EvaluationResult)
            .filter(EvaluationResult.answer_document_id == answer_doc.id)
            .order_by(EvaluationResult.evaluated_at.desc())
            .first()
        )
        
        if eval_result:
            logger.info(f"Re-using existing evaluation result {eval_result.id} for doc {answer_doc.id}")
            # Clear only children scores to avoid FK issues for parallel threads
            self.db.query(QuestionScore).filter(
                QuestionScore.evaluation_result_id == eval_result.id
            ).delete()
            eval_result.total_score = Decimal(0)
            eval_result.overall_feedback = "Grading in progress..."
            eval_result.evaluated_at = func.now() # Reset timestamp
        else:
            # Create fresh result
            eval_result = EvaluationResult(
                answer_document_id=answer_doc.id,
                total_score=Decimal(0),
                overall_feedback="Grading in progress...",
            )
            self.db.add(eval_result)

        self.db.commit() # Save result ID immediately so FKs work in scoring loop
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

            # SPECIFICITY CHECK: Skip parent question if sub-questions are also in the mapping
            if isinstance(target, Question) and getattr(target, 'sub_questions', []):
                sub_mapped = False
                for sq in target.sub_questions:
                    sq_id_str = str(sq.id)
                    sq_label_key = f"{str(target.question_number)}{sq.label}".lower().replace("(", "").replace(")", "")
                    if sq_id_str in answer_doc.mapped_answers or sq_label_key in answer_doc.mapped_answers:
                        sub_mapped = True
                        break
                if sub_mapped:
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

        logger.info(f"Starting grading loop for {len(answer_doc.mapped_answers)} mapped items.")

        for key, student_text in answer_doc.mapped_answers.items():
            target = self._find_matching_question(key, question_map)
            
            if not target:
                logger.warning(f"No question target found for key: '{key}'")
                continue

            target_id = getattr(target, 'id', None)
            display_number = self._resolve_display_number(target, key)
            part_name = getattr(target, 'part_name', 'Unknown')
            
            logger.info(f"Processing question {key} -> ID: {target_id} (Part: {part_name}, Label: {display_number})")

            # Skip if we already graded this specific question/sub-question entry
            if target_id in seen_question_ids:
                logger.warning(f"Skipping duplicate mapping for question: {key} (ID: {target_id})")
                continue
            
            # SPECIFICITY CHECK
            if isinstance(target, Question) and getattr(target, 'sub_questions', []):
                sub_mapped = False
                for sq in target.sub_questions:
                    sq_id_str = str(sq.id)
                    if sq_id_str in answer_doc.mapped_answers:
                        sub_mapped = True
                        break
                
                if sub_mapped:
                    logger.info(f"Hierarchical overlap detected for {key}; scoring parent question.")

            seen_question_ids.add(target_id)
            
            max_marks = self._resolve_max_marks(target)
            reference_text = self._get_reference_context(target, syllabus_text, rubric_text)
            
            processed_count += 1
            if progress_callback:
                pct = 5 + int((processed_count / total_questions) * 65)
                progress_callback("evaluating_answers", f"Scoring question {display_number}...", percent=pct)

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

            scored_items.append({
                "key": key,
                "student_text": student_text,
                "reference_text": reference_text,
                "target": target,
                "max_marks": max_marks,
                "awarded_marks": awarded_marks,
                "display_number": display_number,
                "student_emb": s_emb
            })

        logger.info(f"Scoring loop finished. Scored {len(scored_items)} items total.")

        # -------------------------------------------------------
        # PHASE 2: Batch Gemini feedback & relevance validation
        # -------------------------------------------------------
        eval_data_map: Dict[str, Dict] = {}
        if include_feedback and scored_items:
            if progress_callback:
                progress_callback("generating_feedback", "Generating feedback and validating relevance...", percent=70)

            eval_data_map = self._get_batch_feedback_from_gemini(scored_items)

            if progress_callback:
                progress_callback("generating_feedback", "Feedback batch completed.", percent=95)
        else:
            if progress_callback:
                progress_callback("generating_feedback", "Skipping feedback for now (scoring only).", percent=95)

        # -------------------------------------------------------
        # PHASE 3: Persist QuestionScore rows (with Meaning-based Correction)
        # -------------------------------------------------------
        # -------------------------------------------------------
        # PHASE 3: Integration & Final Totals (Leaf-Only & Best-of-N)
        # -------------------------------------------------------
        if progress_callback:
            progress_callback("finalizing_results", "Integrating meaning-based assessment...", percent=90)

        # 1. Load Paper Config for selection rules
        from app.services.evaluation.paper_config_service import PaperConfigService
        config_service = PaperConfigService(self.db)
        paper_configs = self.db.query(PaperConfig).filter(PaperConfig.evaluation_session_id == eval_session_id).all()
        selection_map = {c.paper_part: c.selection_rules for c in paper_configs if c.selection_rules}

        # 2. Add unattempted questions to scored_items so they show up in summary
        # We use question_map to find all available questions
        all_objs = {id(v): v for v in question_map.values()}.values()
        questions = [q for q in all_objs if isinstance(q, Question)]
        
        all_target_ids = {str(q.id) for q in questions if not isinstance(q, SubQuestion)}
        all_target_ids.update({str(sq.id) for q in questions for sq in getattr(q, 'sub_questions', []) or []})
        
        scored_target_ids = {str(item["target"].id) for item in scored_items}
        
        # Build complete map of all questions for loop
        full_q_map = {}
        for q in questions:
            full_q_map[str(q.id)] = q
            for sq in getattr(q, 'sub_questions', []) or []:
                full_q_map[str(sq.id)] = sq

        # 3. Create QuestionScore records for all attempted and unattempted items
        # Grouped by Part and Main-Question-ID for selection logic later
        part_scores = {} # {part_name: {main_q_id: [scored_item]}}
        
        for q_id, target in full_q_map.items():
            meaning_data = eval_data_map.get(q_id, {}) # Try by UUID
            
            # Find matching item if attempted
            item = next((it for it in scored_items if str(it["target"].id) == q_id), None)
            
            if item:
                # Attempted
                meaning_score = float(meaning_data.get("meaning_score", 0.5))
                system_ratio = float(item["awarded_marks"]) / max(1, item["max_marks"])
                blended_ratio = (0.50 * meaning_score) + (0.50 * system_ratio)
                final_snapped_ratio = self._apply_discrete_bands(blended_ratio, item["max_marks"])
                final_marks = Decimal(str(final_snapped_ratio * item["max_marks"])).quantize(Decimal("0.5"))
                feedback = meaning_data.get("feedback", "පිළිතුර අගය කරන ලදී.")
            else:
                # Unattempted
                final_marks = Decimal(0)
                feedback = "පිළිතුර හමු නොවුණි (0 ලකුණු)."
                item = {
                    "target": target,
                    "max_marks": self._resolve_max_marks(target),
                    "display_number": self._resolve_display_number(target, q_id)
                }

            # Save QuestionScore
            part_name = getattr(target, 'part_name', 'Unknown')
            q_score_params = {
                "evaluation_result_id": eval_result.id,
                "awarded_marks": final_marks,
                "feedback": feedback,
            }
            if isinstance(target, SubQuestion):
                q_score_params["sub_question_id"] = target.id
            else:
                q_score_params["question_id"] = target.id
            
            q_score = QuestionScore(**q_score_params)
            self.db.add(q_score)
            
            # Organize for total calculation
            if part_name not in part_scores:
                part_scores[part_name] = {}
            
            # Leaf logic: Only sum if it has no children
            is_leaf = True
            main_q = target
            if isinstance(target, SubQuestion):
                if getattr(target, 'children', []): is_leaf = False
                main_q = target.question
            else:
                if getattr(target, 'sub_questions', []): is_leaf = False
            
            if is_leaf:
                main_q_id = str(main_q.id) if main_q else "orphan"
                if main_q_id not in part_scores[part_name]:
                    part_scores[part_name][main_q_id] = []
                part_scores[part_name][main_q_id].append(final_marks)

        self.db.flush()

        # 4. Final total score calculation using selection rules
        total_score_val = Decimal(0)
        for part_name, section_map in part_scores.items():
            # Calculate total per main question
            main_q_totals = []
            for mq_id, leaf_marks in section_map.items():
                main_q_totals.append(sum(leaf_marks))
            
            # Apply selection rules (Best of N)
            # rules format: {'total': 4} or {'Part_II': 4}
            part_rules = selection_map.get(part_name) or {}
            required_count = part_rules.get('total') or part_rules.get(part_name)
            
            if required_count and len(main_q_totals) > int(required_count):
                # Sort descending and take top N
                main_q_totals.sort(reverse=True)
                selected_totals = main_q_totals[:int(required_count)]
                logger.info(f"Part {part_name}: Selected {required_count}/{len(main_q_totals)} best questions.")
                total_score_val += sum(selected_totals)
            else:
                total_score_val += sum(main_q_totals)

        eval_result.total_score = total_score_val.quantize(Decimal("0.01"))
        logger.info(f"Final Total Score calculated (selection-aware): {eval_result.total_score}")

        if include_feedback:
            if progress_callback:
                progress_callback("generating_feedback", "Generating overall feedback...", percent=98)

            eval_result.overall_feedback = self._generate_overall_feedback(
                eval_result.total_score, eval_result.id
            )

        if progress_callback:
            progress_callback("completed", "Evaluation completed successfully.", percent=100)

        self.db.commit()
        logger.info(f"Grading transaction committed for result ID: {eval_result.id}")
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
            
            # multiplier = Decimal(str(gemini_data.get("relevance_multiplier", 1.0)))
            # new_score = (item["awarded_marks"] * multiplier).quantize(Decimal("0.01"))
            # qs.awarded_marks = min(Decimal(str(item["max_marks"])), max(Decimal("0"), new_score))
            # Do NOT modify marks during feedback generation
            qs.awarded_marks = item["awarded_marks"]

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
        """Optimized semantic similarity using sentence-level max-match to prevent dilution."""
        if not reference_text or not student_text:
            return 0.0
            
        # Split reference into sentences for max-similarity matching
        # This prevents a short correct answer from being penalized vs a long reference paragraph
        sentences = [s.strip() for s in re.split(r'[.!?\n]', reference_text) if len(s.strip()) > 10]
        if not sentences:
            # Fallback to whole-text if splitting fails
            emb1 = student_emb if student_emb is not None else xlmr.encode(student_text, convert_to_tensor=True)
            emb2 = reference_emb if reference_emb is not None else xlmr.encode(reference_text, convert_to_tensor=True)
            raw_sim = util.cos_sim(emb1, emb2).item()
            return self._sinhala_sigmoid_boost(raw_sim)

        # Encode student text
        s_emb = student_emb if student_emb is not None else xlmr.encode(student_text, convert_to_tensor=True)
        
        # Identify missing sentences from global cache
        missing = [s for s in sentences if s not in self._sentence_cache]
        if missing:
            with ml_semaphore:
                new_embs = xlmr.encode(missing, batch_size=min(len(missing), 32), convert_to_tensor=True)
                for i, s in enumerate(missing):
                    self._sentence_cache[s] = new_embs[i]
        
        # Batch compare against all reference sentences
        ref_embs = torch.stack([self._sentence_cache[s] for s in sentences])
        sims = util.cos_sim(s_emb, ref_embs)[0]
        max_sim = sims.max().item()
        
        return self._sinhala_sigmoid_boost(max_sim)

    def _sinhala_sigmoid_boost(self, sim: float) -> float:
        """
        Map Sinhala cosine similarity to marks with conservative thresholds.
        Sinhala embeddings often cluster; we need to be strict but fair.
        """
        if sim >= 0.65: return 1.0  # Fairer: Was 0.72
        if sim >= 0.52: return 0.50 + (sim - 0.52) * (0.50 / 0.13) # 0.52 -> 0.5, 0.65 -> 1.0
        if sim >= 0.40: return 0.0 + (sim - 0.40) * (0.50 / 0.12)  # 0.40 -> 0.0, 0.52 -> 0.5
        return 0.0


    # ----------------------------------------------------------
    # MARKING BANDS
    # ----------------------------------------------------------
    def _apply_discrete_bands(self, ratio: float, max_marks: int) -> float:
        """
        Dynamically snap to available mark steps (1.0) based on max_marks.
        For Short Answers (<=2 marks), we force whole-mark steps (0, 1, 2) to avoid 1.5/2.
        """
        from decimal import Decimal, ROUND_HALF_UP
        # Thresholding: 0.85+ for full marks, <0.30 for 0 marks
        if ratio >= 0.85: return 1.0
        if ratio < 0.30: return 0.0
        
        # Scaling [0.30, 0.85] to [0.0, 1.0] for fair distribution
        scaled_ratio = (ratio - 0.30) / 0.55
        actual_marks = scaled_ratio * max_marks
        
        # Force whole marks (1.0 step) for small questions and Paper II defaults
        step = Decimal("1.0")
        
        snapped_marks = (Decimal(str(actual_marks)) / step).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * step
        return float(snapped_marks / Decimal(str(max_marks)))

    def _apply_marking_band(self, semantic: float, coverage: float) -> float:
        combined = (0.6 * semantic) + (0.4 * coverage)

        # Stricter, more proportional bands to avoid inflating poor answers
        if combined >= 0.85:
            return 1.0
        if combined >= 0.70:
            return 0.75
        if combined >= 0.55:
            return 0.50
        if combined >= 0.40:
            return 0.25

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

        # STIFFENED: Threshold from 0.45 -> 0.60 for Sinhala concept matching
        hits = int((sims >= 0.60).sum().item())

        # STIFFENED: Divisor from 0.75 -> 0.90
        ratio = hits / max(1, len(sentences) * 0.90)
        return min(1.0, ratio), f"{hits}/{len(sentences)} concepts covered"



    # ----------------------------------------------------------
    # QUESTION MAPPING
    # ----------------------------------------------------------
    def _build_question_map(self, questions: List[Question]) -> Dict[str, Any]:
        """Build a robust map of question IDs and human-readable identifiers."""
        q_map = {}
        for q in questions:
            q_id_str = str(q.id)
            q_num = str(q.question_number).lower().replace(".", "").strip()
            part_name = getattr(q, 'part_name', '').lower().replace(" ", "_").strip()
            
            # 1. UUID Priority (Used by Gemini Mapping)
            q_map[q_id_str] = q
            
            # 2. Part-Specific Names (e.g., 'paper_i_1', 'paper_ii_q1')
            if part_name:
                q_map[f"{part_name}_{q_num}"] = q
            
            # 3. Global Number (Risky, but kept for simple papers)
            # Only add if not already present to avoid overwriting UUIDs or Prefixed keys
            if q_num not in q_map:
                q_map[q_num] = q

            for sq in getattr(q, 'sub_questions', []) or []:
                sq_id_str = str(sq.id)
                sq_label = str(sq.label).lower().replace("(", "").replace(")", "").strip()
                composite_key = f"{q_num}{sq_label}"
                
                q_map[sq_id_str] = sq
                if part_name:
                    q_map[f"{part_name}_{composite_key}"] = sq
                
                if composite_key not in q_map:
                    q_map[composite_key] = sq
                    
        return q_map

    def _find_matching_question(self, key: str, q_map: Dict[str, Any]):
        norm = key.lower().replace(" ", "").replace(".", "").replace("(", "").replace(")", "")
        return q_map.get(key) or q_map.get(norm)

    # ----------------------------------------------------------
    # LOADERS
    # ----------------------------------------------------------
    # These methods are now in AnswerEvaluationService and are no longer needed here.
    

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

    def _calculate_depth_penalty(self, student_text: str, reference_text: str, max_marks: int) -> float:
        """
        Calculate a penalty factor based on the relative length of the student answer.
        Paper II (4 marks) requires depth. If the student answer is too short compared to 
        the reference context, it shouldn't get full marks even if keywords match.
        """
        if max_marks <= 2:
            return 1.0 # Less strict for short answers
            
        student_words = len(re.findall(r'\w+', student_text))
        # Use a more realistic reference length (avg of context sentences) if context is huge
        ref_words = len(re.findall(r'\w+', reference_text))
        
        if ref_words == 0:
            return 1.0
            
        # For history essays, soften penalty to not crush correct concise answers
        if student_words < 12:
            return 0.80 # Was 0.65
        elif student_words < 25:
            return 0.90 # Was 0.85
            
        ratio = student_words / max(1, ref_words * 0.4) 
        if ratio < 0.2:
            return 0.85
            
        return 1.0

    def _calculate_system_score(self, student_text: str, reference_text: str, weights: Dict[str, float], max_marks: int = 1, student_emb=None, reference_emb=None) -> float:
        """Calculate score using discrete snapping for short answers and weighted metrics for essays."""
        if not reference_text or not student_text:
            return 0.0

        # 1. Semantic Score (XLM-R)
        semantic = self._semantic_similarity(student_text, reference_text, student_emb, reference_emb)

        # Handle Short Factual Answers (Paper I Style: <= 2 marks)
        if max_marks <= 2:
            # Combined semantic (80%) and keyword (20%)
            relevance = self._calculate_relevance_score(student_text, reference_text)
            combined = (0.8 * semantic) + (0.2 * relevance)
            return float(combined) # RETURN RAW RATIO (0.0 - 1.0)

        # Handle Essay/Structured Answers (Paper II Style: > 2 marks)
        # 2. Coverage Score (normalized for concise correct answers)
        coverage, _ = self._calculate_coverage_score(student_text, reference_text, max_marks, student_emb)

        # 3. Relevance Score
        relevance = self._calculate_relevance_score(student_text, reference_text)

        # Phase 4: Integration (Balanced weighting)
        # STIFFENED: Reduced semantic dominance for Paper II to require depth
        if max_marks > 2:
            if semantic >= 0.95:
                s_w, c_w, r_w = 0.70, 0.15, 0.15
            else:
                s_w, c_w, r_w = 0.50, 0.25, 0.25
        else:
            if semantic >= 0.92:
                s_w, c_w, r_w = 0.80, 0.10, 0.10
            else:
                s_w, c_w, r_w = 0.60, 0.20, 0.20
            
        score = (s_w * semantic) + (c_w * coverage) + (r_w * relevance)

        # Apply Depth Penalty
        depth_mult = self._calculate_depth_penalty(student_text, reference_text, max_marks)
        score = score * depth_mult

        # RETURN RAW CONTINUOUS RATIO (0.0 - 1.2+ capped at 1.0 eventually in blending)
        return float(score)


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
        # STIFFENED: recall divisor (0.95 instead of 0.7)
        recall = overlap / max(1, len(ref_words) * 0.95)

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
You are a senior examiner in Sri Lanka.
Your goal is to provide a critical "Meaning Assessment".
Different papers have different mark allocations; you must award the `meaning_score` (0.0 to 1.0) based on how complete the student's answer is compared to the 'Reference Context'.

**SCORING CRITERIA (`meaning_score`):**
- `1.0`: The student's answer captures ALL essential facts/meanings.
- `0.8`: Captures the core meaning but misses a specific term or minor detail.
- `0.5`: Only one of several required points is mentioned, or very vague.
- `0.2`: Mentions the right topic but with factual errors or incomplete logic.
- `0.0`: Factually wrong, contradictory, or completely unrelated.

**STRICTNESS RULES:**
- If the answer is marked "සම්පූර්ණයෙන්ම වැරදි" in your internal logic, give `0.0`.
- Do not award marks for filler words.
- If the answer is perfect but concise, give `1.0`.
- For multiple points (e.g., 2 names required), if only 1 is present, give `0.5`.

3. Return as JSON where keys are question keys, and values are objects with strictly 'feedback' and 'meaning_score'.

Example format:
{
  "1": { "feedback": "මාතෘකාවට අදාළයි...", "meaning_score": 1.0 },
  "2අ": { "feedback": "සාවද්‍ය තොරතුරු අඩංගු වේ...", "meaning_score": 0.0 }
}

Questions to evaluate:
"""
        def process_chunk(chunk: List[Dict]) -> Dict[str, Dict]:
            chunk_prompt = base_prompt
            for item in chunk:
                q_text = getattr(item["target"], "question_text", "") or getattr(
                    item["target"], "sub_question_text", ""
                )
                part_name = getattr(item["target"], "part_name", "Unknown Part")
                chunk_prompt += f"\n--- Key: {item['key']} ---\n"
                chunk_prompt += f"Part: {part_name}\n"
                chunk_prompt += f"Question Number: {item['display_number']}\n"
                chunk_prompt += f"Question: {q_text}\n"
                chunk_prompt += f"Target Marks: {item['max_marks']}\n"
                chunk_prompt += f"Student Answer: {item['student_text']}\n"
                chunk_prompt += f"Reference Context: {item['reference_text']}\n"
            
            try:
                # Log keys being sent
                sent_keys = [it["key"] for it in chunk]
                logger.info(f"Sending batch for keys: {sent_keys}")
                
                response_json = self.gemini.generate_content(chunk_prompt, json_mode=True).get("text", "{}")
                try:
                    clean_json = re.sub(r'^```json\s*|\s*```$', '', response_json.strip(), flags=re.MULTILINE)
                    data = json.loads(clean_json)
                    
                    # Log if any keys from chunk are missing in response
                    received_keys = list(data.keys())
                    missing_keys = [k for k in sent_keys if k not in received_keys]
                    if missing_keys:
                        logger.warning(f"Gemini missed keys in response: {missing_keys}")
                    
                    return data
                except Exception as e:
                    logger.error(f"Failed to parse batched feedback JSON: {e}. Raw: {response_json}")
                    return {}
            except Exception as e:
                logger.error(f"Batch Gemini feedback failed: {e}")
                return {}

        # Filter: Skip Gemini for MCQ/Short Answer questions (typically Paper I)
        # to reduce time from 30m to 5m.
        ai_items = [
            it for it in items 
            if getattr(it["target"], "part_name", "").lower() != "paper_i"
        ]
        
        batch_size = 10 # Increased from 5 -> 10
        chunks = [ai_items[i:i + batch_size] for i in range(0, len(ai_items), batch_size)]
        
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

        # Wrap feedback with question identifiers
        final_map = {}
        for item in items:
            key = item["key"]
            part_name = getattr(item["target"], "part_name", "").lower()
            
            # If it was skipped (Paper I), meaning_score acts as a 1.0 pass-through
            if part_name == "paper_i":
                final_map[key] = {
                    "meaning_score": 1.0, 
                    "feedback": f"**ප්‍රශ්නය {item['display_number']}**\n\nස්වයංක්‍රීයව ලකුණු ලබා දෙන ලදී."
                }
                continue

            eval_res_json = evaluation_data.get(key, {})
            meaning_score = eval_res_json.get("meaning_score", 0.5) # Default to 0.5 for stability
            raw_feedback = eval_res_json.get("feedback", "(ප්‍රතිපෝෂණ ලබා ගත නොහැක)")
            
            final_map[key] = {
                "meaning_score": meaning_score,
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
