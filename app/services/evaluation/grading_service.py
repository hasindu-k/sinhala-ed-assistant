#app/services/evaluation/grading_service.py

import logging
import re
import json
import time
from math import floor
from uuid import UUID
from typing import Dict, Any, List, Tuple, Optional, Callable
from decimal import Decimal, ROUND_HALF_UP
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import torch
from rank_bm25 import BM25Okapi
from sentence_transformers import util
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.orm.exc import StaleDataError

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
from app.shared.ai.embeddings import xlmr, ml_semaphore, ensure_sentences_cached, _embedding_cache
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

    def _resolve_part_name(self, target) -> str:
        """
        Correctly resolve the part name for any question or sub-question.
        Sub-questions do not have part_name directly, so we traverse the parent chain.
        """
        # Direct Question object has part_name
        part = getattr(target, 'part_name', None)
        if part:
            return part
        
        # SubQuestion: try .question attribute (direct parent Question)
        if hasattr(target, 'question') and target.question:
            part = getattr(target.question, 'part_name', None)
            if part:
                return part
        
        # Nested SubQuestion: traverse parent chain
        curr = target
        while hasattr(curr, 'parent') and curr.parent:
            curr = curr.parent
            if hasattr(curr, 'question') and curr.question:
                part = getattr(curr.question, 'part_name', None)
                if part:
                    return part
        
        return 'Unknown'



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
            raise ValueError("නිරවද්‍ය ලෙස පිළිතුරු හඳුනා ගැනීමට නොහැකි විය. කරුණාකර නැවත උත්සාහ කරන්න. (AI Mapping/Extraction Failure)")

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
        # PHASE 0: Pre-calculate all embeddings (SPEEDUP)
        # -------------------------------------------------------
        all_context_sentences = []
        if syllabus_text:
            all_context_sentences.extend([s.strip() for s in re.split(r'[.!?\n]', syllabus_text) if len(s.strip()) > 10])
        # Note: rubric_text is no longer used as context sentences because it contains weights/config, not content.
        
        for key, student_text in answer_doc.mapped_answers.items():
            if isinstance(student_text, str) and student_text.strip().lower() not in ["null", "none", ""]:
                all_context_sentences.append(student_text)
            target = self._find_matching_question(key, question_map)
            if target:
                q_text = getattr(target, "question_text", "") or getattr(target, "sub_question_text", "")
                if q_text:
                    all_context_sentences.append(q_text)
                ref = self._get_reference_context(target, syllabus_text, rubric_text)
                if ref:
                    all_context_sentences.extend([s.strip() for s in re.split(r'[.!?\n]', ref) if len(s.strip()) > 10])

        if progress_callback:
            progress_callback("evaluating_answers", "Mass-calculating sentence features...", percent=5)
        
        ensure_sentences_cached(all_context_sentences)

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

            if not student_text or str(student_text).strip().lower() in ["null", "none", ""]:
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

        all_student_texts = [item[1] for item in score_inputs if item[1]]
        all_ref_texts = list(set([item[4] for item in score_inputs if item[4]]))
        # Maps for quick lookup: text -> embedding tensor
        student_emb_map = {text: _embedding_cache.get(text) for text in all_student_texts}
        ref_emb_map = {text: _embedding_cache.get(text) for text in all_ref_texts}

        scored_items: List[Dict] = []
        seen_question_ids = set()  # To prevent duplicates in the final result
        seen_keys = set()          # Also track by key to catch mapping noise

        logger.info(f"Starting grading loop for {len(answer_doc.mapped_answers)} mapped items.")

        for key, student_text in answer_doc.mapped_answers.items():
            target = self._find_matching_question(key, question_map)
            
            if not target:
                logger.warning(f"No question target found for key: '{key}'")
                continue

            # CRITICAL FIX: Ignore empty answers so they are treated as "Unattempted"
            # instead of being scored and getting default AI meaning marks.
            if not student_text or str(student_text).strip().lower() in ["null", "none", ""]:
                logger.info(f"Skipping empty answer for key: '{key}'")
                continue

            # Resolve part_name correctly for sub-questions by traversing parent chain
            target_id = getattr(target, 'id', None)
            display_number = self._resolve_display_number(target, key)
            part_name = self._resolve_part_name(target)
            
            logger.info(f"Processing question {key} -> ID: {target_id} (Part: {part_name}, Label: {display_number})")

            # Skip if we already graded this specific question/sub-question entry (Fix 3)
            if target_id in seen_question_ids or key in seen_keys:
                logger.warning(f"Skipping duplicate mapping for question: {key} (ID: {target_id})")
                continue
            
            # SPECIFICITY CHECK — skip parent if sub-questions are mapped (Fix 1)
            if isinstance(target, Question) and getattr(target, 'sub_questions', []):
                sub_mapped = False
                for sq in target.sub_questions:
                    sq_id_str = str(sq.id)
                    sq_label_key = f"{str(target.question_number)}{sq.label}".lower().replace("(", "").replace(")", "")
                    if sq_id_str in answer_doc.mapped_answers or sq_label_key in answer_doc.mapped_answers:
                        sub_mapped = True
                        break
                
                if sub_mapped:
                    logger.info(f"Skipping parent question {key} because sub-questions are mapped.")
                    continue  # <-- CRITICAL: was missing, causing parent to still be scored

            seen_question_ids.add(target_id)
            seen_keys.add(key)
            
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

            batch_results = self._get_batch_feedback_from_gemini(scored_items)
            eval_data_map.update(batch_results)

            if progress_callback:
                progress_callback("generating_feedback", "Feedback batch completed.", percent=95)
        else:
            if progress_callback:
                progress_callback("generating_feedback", "Using system-only scoring (Gemini skipped).", percent=95)

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
        eval_session = self.db.query(EvaluationSession).filter(EvaluationSession.id == eval_session_id).first()
        chat_session_id = eval_session.session_id if eval_session else None
        
        config_service = PaperConfigService(self.db)
        # Fetch by both IDs to ensure we get the confirmed config from the chat session
        paper_configs = self.db.query(PaperConfig).filter(
            (PaperConfig.evaluation_session_id == eval_session_id) | 
            (PaperConfig.chat_session_id == chat_session_id)
        ).all()
        # NORMALIZE keys to paper_i, paper_ii for robust matching
        selection_map = {}
        for c in paper_configs:
            if c.selection_rules:
                norm_key = c.paper_part.lower().replace(" ", "_")
                # FIX: Use endswith to avoid 'paper_ii'.contains('i') ambiguity
                if norm_key.endswith("_ii") or norm_key == "paper_ii":
                    norm_key = "paper_ii"
                elif norm_key.endswith("_i") or norm_key == "paper_i":
                    norm_key = "paper_i"

                selection_map[norm_key] = c.selection_rules

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
            # Find matching item if attempted
            item = next((it for it in scored_items if str(it["target"].id) == q_id), None)
            
            # Normalize part name for grouping and rules - use helper for sub-questions
            raw_part = self._resolve_part_name(target)
            
            part_name = raw_part.lower().replace(" ", "_")
            # FIX: Use endswith to avoid 'paper_ii'.contains('i') being True
            if part_name.endswith("_ii") or part_name == "paper_ii":
                part_name = "paper_ii"
            elif part_name.endswith("_i") or part_name == "paper_i":
                part_name = "paper_i"
            # else: keep as-is (unknown, etc.)


            if item:
                # Attempted
                meaning_data = eval_data_map.get(item["key"], {})
                # FIX: Gemini returns 'meaning_score', not 'relevance_multiplier'
                meaning_score = float(meaning_data.get("meaning_score", meaning_data.get("relevance_multiplier", 0.5)))
                system_ratio = float(item["awarded_marks"]) / max(1, item["max_marks"])
                
                # UNIVERSAL BLENDING STRATEGY (Accuracy & Weights):
                # The System (XLM-R) is the HERO. Gemini validates logical correctness.
                system_score_ratio = system_ratio 
                
                # LOGIC:
                # 1. If Gemini says Meaning is Correct (>=0.75), trust the system's semantic match.
                # 2. If Gemini says Meaning is Wrong (<=0.20), cap the score.
                # 3. Otherwise, blend heavily towards the System for consistency.
                
                if meaning_score >= 0.75:
                    # AI confirms logic matches reference meaning
                    # We boost the system score to full marks if the system also found a strong match (>0.5)
                    # or keep the system score if it was already high.
                    blended_ratio = max(system_score_ratio, 1.0 if system_score_ratio > 0.4 else system_score_ratio)
                elif meaning_score <= 0.20:
                    # AI identifies factual failure; marks are capped tightly
                    blended_ratio = min(system_score_ratio, meaning_score)
                else:
                    # Blend with System leading (60% System, 40% AI)
                    blended_ratio = (0.4 * meaning_score) + (0.6 * system_score_ratio)
                
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
            # BUG FIX: Do NOT re-assign part_name here as it overwrites normalized values (paper_i, paper_ii)
            
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
                    part_scores[part_name][main_q_id] = {"marks": [], "attempted": 0}
                part_scores[part_name][main_q_id]["marks"].append(final_marks)
                # Count as "attempted" if the student actually submitted an answer
                if item and item in scored_items:
                    part_scores[part_name][main_q_id]["attempted"] += 1


        self.db.flush()

        # 4. Final total score calculation using selection rules
        total_score_val = Decimal(0)
        
        # Normalize selection_map keys for robust lookup
        norm_selection_map = {k.lower().replace(" ", "_"): v for k, v in selection_map.items()}

        for part_name, section_map in part_scores.items():
            # Calculate total per main question, tracking attempt status
            main_q_entries = []
            for mq_id, data in section_map.items():
                total = sum(data["marks"])
                attempted = data["attempted"]  # number of sub-questions actually answered
                main_q_entries.append((total, attempted))
            
            # Apply selection rules (Best of N)
            part_rules = norm_selection_map.get(part_name) or {}
            mode = part_rules.get('mode', 'all')
            count = part_rules.get('count') or part_rules.get('total')
            
            if mode == 'any' and count and len(main_q_entries) > int(count):
                # CRITICAL: Sort by (attempted DESC, score DESC)
                # Questions the student actually answered always rank above unanswered ones,
                # regardless of score. This prevents mapping noise from displacing real answers.
                main_q_entries.sort(key=lambda x: (x[1], x[0]), reverse=True)
                selected = main_q_entries[:int(count)]
                selected_totals = [e[0] for e in selected]
                attempted_count = sum(1 for e in selected if e[1] > 0)
                logger.info(f"Part {part_name}: Selected {count}/{len(main_q_entries)} best questions ({attempted_count} attempted).")
                total_score_val += sum(selected_totals)
            else:
                total_score_val += sum(e[0] for e in main_q_entries)

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
        # RELOAD QuestionScore objects safely to prevent StaleDataError
        current_scores = {qs.id: qs for qs in self.db.query(QuestionScore).filter(QuestionScore.evaluation_result_id == result.id).all()}
        
        for item in scored_items:
            # Match by original DB score object ID
            qs_id = item["db_score_obj"].id
            qs = current_scores.get(qs_id)
            
            if not qs:
                logger.warning(f"QuestionScore {qs_id} no longer exists. Skipping feedback update for this row.")
                continue

            gemini_data = eval_data_map.get(item["key"], {})
            feedback = gemini_data.get("feedback")
            # Do NOT modify marks during feedback generation (already evaluated)
            if feedback:
                qs.feedback = feedback

        # 7. Generate overall feedback
        result.overall_feedback = overall_feedback
        
        try:
            self.db.commit()
            logger.info(f"Feedback successfully saved for result {result.id}")
        except StaleDataError:
            self.db.rollback()
            logger.error(f"StaleDataError while saving feedback for result {result.id}. This usually happens if a re-evaluation was triggered concurrently.")
            # We don't raise here because the grading itself was already committed previously
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error while committing feedback: {e}")
            raise

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
            with ml_semaphore:
                emb1 = student_emb if student_emb is not None else _embedding_cache.get(student_text)
                if emb1 is None: emb1 = xlmr.encode(student_text, convert_to_tensor=True)
                
                emb2 = reference_emb if reference_emb is not None else _embedding_cache.get(reference_text)
                if emb2 is None: emb2 = xlmr.encode(reference_text, convert_to_tensor=True)
                
            raw_sim = util.cos_sim(emb1, emb2).item()
            return self._sinhala_sigmoid_boost(raw_sim)

        # Encode student text if not provided
        s_emb = student_emb if student_emb is not None else _embedding_cache.get(student_text)
        if s_emb is None:
            with ml_semaphore:
                s_emb = xlmr.encode(student_text, convert_to_tensor=True)
        
        # All reference sentences MUST be in global cache due to pre-batching
        # If not, we have a safety fallback
        missing = [s for s in sentences if s not in _embedding_cache]
        if missing:
            ensure_sentences_cached(missing)
        
        # Batch compare against all reference sentences
        ref_embs = torch.stack([_embedding_cache[s] for s in sentences])
        sims = util.cos_sim(s_emb, ref_embs)[0]
        max_sim = sims.max().item()
        
        return self._sinhala_sigmoid_boost(max_sim)

    def _sinhala_sigmoid_boost(self, sim: float) -> float:
        """
        Map Sinhala cosine similarity to marks.
        XLM-R on Sinhala OCR text vs clean syllabus text clusters lower than
        Indo-European languages, so we use more lenient thresholds.
        """
        # CALIBRATED: Lowered full-marks threshold to be more realistic for Sinhala OCR
        if sim >= 0.52: return 1.0          # Was 0.60
        if sim >= 0.40: return 0.50 + (sim - 0.40) * (0.50 / 0.12)  # Was 0.48
        if sim >= 0.28: return 0.0 + (sim - 0.28) * (0.50 / 0.12)   # Was 0.35
        return 0.0


    # ----------------------------------------------------------
    # MARKING BANDS
    # ----------------------------------------------------------
    def _apply_discrete_bands(self, ratio: float, max_marks: int) -> float:
        """
        Dynamically snap to available mark steps (1.0) based on max_marks.
        For Short Answers (<=2 marks), we force whole-mark steps (0, 1, 2) to avoid 1.5/2.
        """
        # CALIBRATED: 0.55+ for full marks (was 0.65)
        # Sinhala OCR produces lower similarity scores against clean syllabus text.
        if ratio >= 0.55: return 1.0
        if ratio < 0.05: return 0.0
        
        # Scaling [0.05, 0.55] to [0.0, 1.0]
        scaled_ratio = (ratio - 0.05) / 0.50
        actual_marks = scaled_ratio * max_marks
        
        # Snap to marks (1.0 step for whole, 0.5 for half)
        # For small marks (<= 2), we usually want whole numbers.
        step = Decimal("1.0") if max_marks <= 2 else Decimal("0.5")
        
        snapped_marks = (Decimal(str(actual_marks)) / step).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * step
        
        # Safety: Ensure it doesn't exceed 1.0 ratio
        final_ratio = float(snapped_marks / Decimal(str(max_marks)))
        return min(1.0, final_ratio)

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
        # GOLD STANDARD: Prioritize structured correct answer if available
        # This guarantees 100% accuracy for MCQ/Short answers with defined keys
        correct = getattr(question, "correct_answer", None)
        if correct and len(correct.strip()) > 0:
            logger.info(f"Using Gold Standard context for question {getattr(question, 'id')}")
            return correct.strip()

        q_number = getattr(question, "question_number", "") or getattr(question, "label", "")
        q_text = getattr(question, "question_text", "") or getattr(
            question, "sub_question_text", ""
        )
        
        # PRECEDENCE: Searching Syllabus is the source of knowledge.
        source = syllabus_text
        if not source:
            return ""

        # Use finer splitting to ZOOM in on the exact marking point
        chunks = [c.strip() for c in source.split("\n") if len(c.strip()) > 5]
        
        # Boost lines that contain the question number
        search_query = f"{q_number} {q_text}"
        bm25 = BM25Okapi([c.split() for c in chunks])
        
        # Get more chunks but shorter ones to find the needle in the haystack
        top_chunks = bm25.get_top_n(search_query.split(), chunks, n=15)
        
        # Filter: If we found chunks starting with the question number, prioritize them!
        # Enhanced pattern to match "01", "1.", "(1)", "1 " at start of line
        prio_chunks = [c for c in top_chunks if re.match(rf"^(?:\()?0?{q_number}(?:\.|\)|[\s:]|$)", c.strip())]
        
        if prio_chunks:
            context = "\n\n".join(prio_chunks[:5])
        else:
            # Look for chunks that contain the number anywhere if no "start" matches
            backup_prio = [c for c in top_chunks if f"{q_number}" in c]
            if backup_prio:
                context = "\n\n".join(backup_prio[:5])
            else:
                context = "\n\n".join(top_chunks[:5])
        
        if len(context) > 2000:
            context = context[:2000] + "... [Context Clipped]"
        return context

    def _calculate_coverage_score(self, student_text: str, reference_text: str, max_marks: int, student_emb=None):
        """
        Optimized: batch-encodes all reference sentences in a single XLM-R forward pass
        instead of one pass per sentence.
        """
        if not reference_text:
            return 0.0, "No reference"

        sentences = re.split(r"(?<=[.!?])\s+", reference_text)
        # RELAXED: Reduce from 10 to 4 to capture Sinhala keywords/marking points
        sentences = [s.strip() for s in sentences if len(s.strip()) >= 4]

        if not sentences:
            return 0.0, "No reference sentences"

        # Use cached student embedding if provided
        s_emb = student_emb if student_emb is not None else _embedding_cache.get(student_text)
        if s_emb is None:
            with ml_semaphore:
                s_emb = xlmr.encode(student_text, convert_to_tensor=True)
                with _cache_lock: _embedding_cache[student_text] = s_emb

        # -------------------------------------------------------
        # Identify sentences not yet in the cache
        # -------------------------------------------------------
        missing_sentences = [s for s in sentences if s not in _embedding_cache]
        
        if missing_sentences:
            ensure_sentences_cached(missing_sentences)

        # Assemble the full matrix of embeddings for THIS question
        sentence_embs = torch.stack([_embedding_cache[s] for s in sentences])

        # Cosine similarities in one matrix operation
        sims = util.cos_sim(s_emb, sentence_embs)[0]  # shape: (num_sentences,)

        # RELAXED: Threshold from 0.55 -> 0.45 for Sinhala concept matching (Short Answers)
        threshold = 0.45 if max_marks <= 2 else 0.55
        hits = int((sims >= threshold).sum().item())

        # RELAXED: Divisor from 0.80 -> 0.70
        ratio = hits / max(1, len(sentences) * 0.70)
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
        default_weights = {"semantic": 0.8, "coverage": 0.1, "relevance": 0.1}

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

        semantic = self._semantic_similarity(student_text, reference_text, student_emb, reference_emb)
        relevance = self._calculate_relevance_score(student_text, reference_text)

        # DEBUG: Log raw scores to help calibrate thresholds
        logger.debug(f"[SCORE] semantic={semantic:.3f} relevance={relevance:.3f} max_marks={max_marks} | answer='{student_text[:60]}'")

        s_w = float(weights.get("semantic", 0.70))
        c_w = float(weights.get("coverage", 0.15))
        r_w = float(weights.get("relevance", 0.15))

        # Normalize weights
        total_w = s_w + c_w + r_w
        if total_w > 0:
            s_w /= total_w
            c_w /= total_w
            r_w /= total_w

        # Handle Short Factual Answers (Paper I Style: <= 2 marks)
        if max_marks <= 2:
            # ADDITION: Marker Match (Direct lookup in context for MCQ)
            s_clean = student_text.strip().lower().replace(".", "").replace("(", "").replace(")", "")
            if len(s_clean) <= 2:
                pattern = rf"(?:\({s_clean}\)|[\s.]{s_clean}[\s.]|^{s_clean}[\s.]|[\s.]{s_clean}$)"
                if re.search(pattern, reference_text.lower()):
                    return 1.0

            # Use Weights (leaning into semantic meaning)
            # For short answers, we redistribute coverage weight to semantic
            i_s_w = s_w + c_w
            i_r_w = r_w
            combined = (i_s_w * semantic) + (i_r_w * relevance)
            return float(combined)

        # Handle Essay/Structured Answers (Paper II Style: > 2 marks)
        coverage, _ = self._calculate_coverage_score(student_text, reference_text, max_marks, student_emb)

        score = (s_w * semantic) + (c_w * coverage) + (r_w * relevance)

        # Apply Depth Penalty
        depth_mult = self._calculate_depth_penalty(student_text, reference_text, max_marks)
        score = score * depth_mult

        return float(score)


    def _calculate_relevance_score(self, student_text: str, reference_text: str) -> float:
        """Calculate relevance using keyword recall with lenient filtering."""
        if not reference_text or not student_text:
            return 0.0

        def get_keywords(text):
            words = re.findall(r'\w+', text.lower())
            # For short answers or MCQ labels, don't filter out 1-2 char words
            return set([w for w in words if len(w) >= 1])

        student_words = get_keywords(student_text)
        ref_words = get_keywords(reference_text)

        if not ref_words:
            return 1.0

        overlap = len(student_words & ref_words)
        
        # RELAXED: For short student answers, don't penalize based on reference length.
        # This prevents 2000-char context from crushing a 5-word correct answer.
        if len(student_words) < 10:
            recall = overlap / max(1, len(student_words)) # Use Precision-like recall
        else:
            recall = overlap / max(1, len(ref_words) * 0.75) # Much more lenient divisor

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
You are a senior examiner specializing in Sinhala language and logical assessment.
Your role is to help the scoring system by determining if a student's answer is **logically correct** and matches the **meaning** of the reference context, regardless of phrasing.

**SCORING CRITERIA (`meaning_score`):**
- `1.0`: Perfect logic and accuracy. The meaning is exactly what is required.
- `0.8`: Logically sound and correct, even if phrasing or minor details differ.
- `0.5`: Partially correct logic, or mentions only one of several required points.
- `0.2`: Related topic but contains logical fallacies or serious factual errors.
- `0.0`: Completely unrelated, logically wrong, or factually false.

**SPECIAL RULE FOR SHORT ANSWERS (Target Marks <= 2):**
- These questions usually require only a single name, fact, or short phrase.
- DO NOT penalize for lack of elaboration or brevity.
- If the student provides the correct fact/name as per the context, give `meaning_score: 1.0`.

**IMPORTANT:**
1. Focus on **Meaning** over literal text matches. Sinhala has many synonyms and grammatical variations.
2. If the student missed certain concepts, you MUST explicitly state the missing points using phrases like "අඩංගු විය යුතුය", "මඟ හැරී ඇත", "සඳහන් කළ යුතුය", or "පැහැදිලි කළ යුතුය". The system relies on these keywords to extract 'Missing Concepts' and 'Improvement Points'. Be encouraging but accurate.
3. Return the results as a JSON object strictly using the exact UUID "Key" provided for each question as the property name.

Example format:
{
  "550e8400-e29b-41d4-a716-446655440000": { "feedback": "මාතෘකාවට අදාළයි. නමුත් [X] අඩංගු විය යුතුය...", "relevance_multiplier": 1.0 },
  "123e4567-e89b-12d3-a456-426614174000": { "feedback": "මෙම පිළිතුර ප්රශ්නයට අදාළ නැත...", "relevance_multiplier": 0.0 }
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
                chunk_prompt += f"Student Answer: {str(item['student_text'])[:500]}\n"  # Cap to 500 chars
                chunk_prompt += f"Reference Context: {str(item['reference_text'])[:600]}\n"  # Cap to 600 chars

            
            try:
                # Log keys being sent
                sent_keys = [it["key"] for it in chunk]
                logger.info(f"Sending batch for keys: {sent_keys}")
                
                response_json = self.gemini.generate_content(chunk_prompt, json_mode=True).get("text", "{}")
                try:
                    clean_json = re.sub(r'^```json\s*|\s*```$', '', response_json.strip(), flags=re.MULTILINE)
                    data = json.loads(clean_json)
                    
                    # FIX: Handle if Gemini returns a list of dictionaries instead of one object
                    if isinstance(data, list):
                        merged_data = {}
                        for item_dict in data:
                            if isinstance(item_dict, dict):
                                merged_data.update(item_dict)
                        data = merged_data

                    # Log if any keys from chunk are missing in response
                    received_keys = list(data.keys()) if isinstance(data, dict) else []
                    missing_keys = [k for k in sent_keys if k not in received_keys]
                    if missing_keys:
                        logger.warning(f"Gemini missed keys in response: {missing_keys}")
                    
                    # SANITIZE: truncate overly long or corrupted feedback fields
                    import re as _re
                    if isinstance(data, dict):
                        for q_key, q_val in data.items():
                            if isinstance(q_val, dict):
                                fb = q_val.get("feedback", "")
                                if fb:
                                    # Remove repeated single-character sequences (corruption pattern)
                                    fb = _re.sub(r'(.)\1{10,}', r'\1\1\1', fb)
                                    # Cap feedback to 600 chars
                                    q_val["feedback"] = fb[:600]
                    
                    return data
                except Exception as e:
                    logger.error(f"Failed to parse batched feedback JSON: {e}. Raw: {response_json}")
                    return {}
            except Exception as e:
                logger.error(f"Batch Gemini feedback failed: {e}")
                return {}

        # No longer skipping Paper I. All questions benefit from Meaning Assessment.
        ai_items = items
        
        batch_size = 5 # Reduced from 10 -> 5 to stay within context limits
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
