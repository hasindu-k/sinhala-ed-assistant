import logging
from uuid import UUID
from typing import Dict, Any, List, Optional
from decimal import Decimal
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import util

from sqlalchemy.orm import Session
from app.shared.models.answer_evaluation import AnswerDocument, EvaluationResult, QuestionScore
from app.shared.models.question_papers import Question, SubQuestion
from app.shared.models.rubrics import RubricCriterion
from app.shared.models.session_resources import SessionResource
from app.shared.models.resource_file import ResourceFile
from app.shared.ai.embeddings import xlmr
from app.core.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

class GradingService:
    def __init__(self, db: Session):
        self.db = db
        self.gemini = GeminiClient()

    def grade_answer_document(self, answer_doc_id: UUID, user_id: UUID):
        """
        Orchestrates the grading process for a single answer document.
        """
        # 1. Fetch Context
        answer_doc = self.db.query(AnswerDocument).filter(AnswerDocument.id == answer_doc_id).first()
        if not answer_doc:
            raise ValueError("Answer document not found")

        if not answer_doc.mapped_answers:
            raise ValueError("Answer document has not been mapped yet")

        # Fetch Evaluation Session to get Rubric and Question Paper
        from app.shared.models.evaluation_session import EvaluationSession
        eval_session = self.db.query(EvaluationSession).filter(EvaluationSession.id == answer_doc.evaluation_session_id).first()
        
        # Fetch Rubric Text (Needed for fallback)
        rubric_text = ""
        # Try attached rubric resource first
        rubric_res = self.db.query(SessionResource).filter(
            SessionResource.session_id == eval_session.session_id,
            SessionResource.label == "rubric"
        ).first()
        
        if rubric_res:
            res_file = self.db.query(ResourceFile).filter(ResourceFile.id == rubric_res.resource_id).first()
            if res_file:
                rubric_text = res_file.extracted_text

        # Fallback: Check for Structured Rubric if no file-based rubric text found
        if not rubric_text and eval_session.rubric_id:
            from app.shared.models.rubrics import Rubric, RubricCriterion
            rubric = self.db.query(Rubric).filter(Rubric.id == eval_session.rubric_id).first()
            if rubric:
                criteria = self.db.query(RubricCriterion).filter(RubricCriterion.rubric_id == rubric.id).all()
                rubric_text = f"Rubric Name: {rubric.name}\nDescription: {rubric.description}\n\nGeneral Criteria:\n"
                for c in criteria:
                    rubric_text += f"- {c.criterion} (Weight: {c.weight_percentage}%)\n"

        # Fetch Syllabus Text (New Requirement)
        syllabus_text = ""
        syllabus_res = self.db.query(SessionResource).filter(
            SessionResource.session_id == eval_session.session_id,
            SessionResource.label == "syllabus"
        ).first()
        
        if syllabus_res:
            res_file = self.db.query(ResourceFile).filter(ResourceFile.id == syllabus_res.resource_id).first()
            if res_file:
                syllabus_text = res_file.extracted_text

        # Fetch Questions
        from app.services.evaluation.question_paper_service import QuestionPaperService
        qp_service = QuestionPaperService(self.db)
        qps = qp_service.get_question_papers_by_chat_session(eval_session.session_id)
        if not qps:
            raise ValueError("Question paper not found")
        
        questions = qp_service.get_questions_by_paper(qps[0].id) # Assuming single paper for now

        # Create Evaluation Result Record
        eval_result = EvaluationResult(
            answer_document_id=answer_doc.id,
            total_score=0,
            overall_feedback="Grading in progress..."
        )
        self.db.add(eval_result)
        self.db.commit()

        total_score = Decimal(0)
        
        # 2. Iterate and Grade
        # Flatten questions to easily find by label/number
        question_map = self._build_question_map(questions)

        for key, student_text in answer_doc.mapped_answers.items():
            logger.info(f"Starting grading for question {key}...")
            # key might be "1", "1(a)", "Q1.a" etc.
            target_q = self._find_matching_question(key, question_map)
            
            if not target_q:
                logger.warning(f"Could not find question for answer key: {key}")
                continue

            # Determine max marks
            max_marks = target_q.max_marks if hasattr(target_q, 'max_marks') else 0
            if not max_marks:
                continue

            # Extract Reference Context from Syllabus (or Rubric if Syllabus missing)
            reference_text = self._get_reference_context(target_q, syllabus_text, rubric_text)

            # Calculate Score (Pure Semantic)
            score_ratio, _ = self._calculate_semantic_score(
                student_text, 
                reference_text, 
                max_marks
            )
            
            awarded_marks = Decimal(score_ratio * float(max_marks))
            total_score += awarded_marks
            
            logger.info(f"Completed grading for question {key}. Awarded: {awarded_marks}/{max_marks}")

            # Generate Feedback using Gemini (Style, Missing Concepts, Corrections)
            feedback = self._generate_feedback_with_gemini(
                student_text,
                reference_text,
                target_q,
                awarded_marks,
                max_marks
            )

            # Save Question Score
            # We need to link to a SubQuestion if possible, or Question
            # The schema links to SubQuestion. If it's a main question, we might need a dummy subquestion or adjust schema.
            # For now, assuming target_q is a SubQuestion or we treat Question as one.
            
            sub_q_id = target_q.id
            # If target_q is a Question (main), we might need to handle it. 
            # But QuestionScore links to sub_question_id. 
            # Let's assume for now we only grade leaf nodes (SubQuestions).
            # If mapped_answers points to a Main Question that has children, we might be in trouble.
            # But usually mapping maps to the specific part.
            
            # Check if target_q is Question or SubQuestion
            if isinstance(target_q, Question):
                # If it's a main question without subquestions, we can't link it to sub_question_id directly 
                # unless we change schema or have a 1-to-1 mapping.
                # For this implementation, I'll skip saving if it's a main question to avoid FK error, 
                # OR we need to fix the schema. 
                # Let's check if we can find a "default" subquestion or if we should create one.
                pass 
            else:
                qs = QuestionScore(
                    evaluation_result_id=eval_result.id,
                    sub_question_id=sub_q_id,
                    awarded_marks=awarded_marks,
                    feedback=feedback
                )
                self.db.add(qs)

        # 3. Finalize
        eval_result.total_score = total_score
        eval_result.overall_feedback = self._generate_overall_feedback(total_score, eval_result.id)
        self.db.commit()
        
        return eval_result

    def _get_reference_context(self, question: Any, syllabus_text: str, rubric_text: str) -> str:
        """
        Finds the most relevant section from Syllabus (primary) or Rubric (secondary)
        using BM25 retrieval.
        """
        q_text = getattr(question, 'question_text', '') or getattr(question, 'sub_question_text', '')
        
        # Prefer Syllabus, fallback to Rubric
        source_text = syllabus_text if syllabus_text else rubric_text
        
        if not source_text:
            return ""

        # Simple chunking by paragraphs
        chunks = [c.strip() for c in source_text.split('\n\n') if c.strip()]
        if not chunks:
            chunks = [c.strip() for c in source_text.split('\n') if c.strip()]
            
        if not chunks:
            return source_text[:1000] # Fallback

        # Tokenize for BM25
        tokenized_chunks = [chunk.split() for chunk in chunks]
        bm25 = BM25Okapi(tokenized_chunks)
        
        tokenized_query = q_text.split()
        top_chunks = bm25.get_top_n(tokenized_query, chunks, n=1)
        
        return top_chunks[0] if top_chunks else ""

    def _calculate_semantic_score(self, student_text: str, reference_text: str, max_marks: int) -> tuple[float, str]:
        """
        Calculates score based purely on Semantic Similarity (XLM-R) between student answer and reference text.
        NO Gemini involvement.
        """
        if not reference_text:
            return 0.0, "No reference material found in Syllabus/Rubric."

        try:
            # XLM-R Score (Semantic Similarity)
            emb1 = xlmr.encode(student_text, convert_to_tensor=True)
            emb2 = xlmr.encode(reference_text, convert_to_tensor=True)
            cosine_score = util.cos_sim(emb1, emb2).item()
            
            # Clip to 0-1
            semantic_score = max(0.0, min(1.0, cosine_score))
            
            # Heuristic: If similarity is very low (< 0.2), it's probably wrong.
            # If it's high (> 0.7), it's full marks.
            # Let's scale it a bit to be more generous or strict.
            # For now, raw cosine score.
            
            feedback = f"Graded based on semantic similarity ({semantic_score:.2f}) with syllabus content."
            return semantic_score, feedback
            
        except Exception as e:
            logger.error(f"Semantic scoring failed: {e}")
            return 0.0, "Scoring failed."

    def _build_question_map(self, questions: List[Question]) -> Dict[str, Any]:
        """
        Builds a lookup map: "1" -> Q1, "1(a)" -> SQ_a, "uuid" -> Q/SQ
        """
        q_map = {}
        for q in questions:
            # Map UUID
            q_map[str(q.id)] = q
            
            # Normalize Q number
            q_num = str(q.question_number).strip().lower().replace(".", "")
            q_map[q_num] = q
            
            if q.sub_questions:
                for sq in q.sub_questions:
                    # Map UUID
                    q_map[str(sq.id)] = sq
                    
                    # Normalize label
                    sq_label = str(sq.label).strip().lower().replace("(", "").replace(")", "")
                    # Map "1a", "1.a", "a" (if unique context)
                    key = f"{q_num}{sq_label}"
                    q_map[key] = sq
                    q_map[f"{q_num}.{sq_label}"] = sq
                    q_map[f"{q_num}({sq_label})"] = sq
        return q_map

    def _find_matching_question(self, key: str, q_map: Dict[str, Any]):
        # 1. Try exact match (UUIDs usually match here)
        if key in q_map:
            return q_map[key]
            
        # 2. Try normalized match
        norm_key = str(key).strip().lower().replace(" ", "").replace(".", "").replace("(", "").replace(")", "")
        if norm_key in q_map:
            return q_map[norm_key]
        
        return None

    def _extract_model_answer(self, rubric_text: str, question: Any, q_label: str) -> str:
        """
        Uses Gemini to extract the relevant marking criteria for a specific question.
        """
        if not rubric_text:
            return ""

        q_text = getattr(question, 'question_text', '') or getattr(question, 'sub_question_text', '')
        
        prompt = f"""
        You are a helpful assistant extracting marking schemes.
        
        Rubric/Marking Scheme:
        {rubric_text[:10000]} ... (truncated)
        
        Question {q_label}: "{q_text}"
        
        Task: Extract the specific model answer or marking points for Question {q_label} from the Rubric.
        Return ONLY the relevant text.
        """
        
        try:
            response = self.gemini.generate_content(prompt)
            return response.get("text", "").strip()
        except Exception:
            return ""

    def _calculate_score_and_feedback(self, student_text: str, model_text: str, max_marks: int, question: Any) -> tuple[float, str]:
        """
        Calculates score (0.0 to 1.0) and generates feedback.
        """
        semantic_score = 0.0
        raw_bm25 = 0.0
        
        if model_text:
            # 1. BM25 Score (Keyword Relevance)
            tokenized_student = student_text.split()
            tokenized_model = model_text.split()
            
            if tokenized_model and tokenized_student:
                bm25 = BM25Okapi([tokenized_model])
                bm25_scores = bm25.get_scores(tokenized_student)
                raw_bm25 = sum(bm25_scores)
            
            # 2. XLM-R Score (Semantic Similarity)
            try:
                emb1 = xlmr.encode(student_text, convert_to_tensor=True)
                emb2 = xlmr.encode(model_text, convert_to_tensor=True)
                cosine_score = util.cos_sim(emb1, emb2).item()
                semantic_score = max(0.0, min(1.0, cosine_score))
            except Exception as e:
                logger.warning(f"XLM-R encoding failed: {e}")

        # 3. Gemini Grading (The Judge)
        q_text = getattr(question, 'question_text', '') or getattr(question, 'sub_question_text', '')
        
        if model_text:
            prompt = f"""
            You are an expert examiner. Grade this answer.
            
            Question: {q_text}
            Max Marks: {max_marks}
            
            Model Answer / Criteria:
            {model_text}
            
            Student Answer:
            {student_text}
            
            AI Metrics:
            - Semantic Similarity (XLM-R): {semantic_score:.2f} / 1.0
            - Keyword Overlap Signal (BM25): {raw_bm25:.2f} (Higher is better)
            
            Task:
            1. Assign a score out of {max_marks}.
            2. Provide brief feedback.
            
            Output Format (JSON):
            {{
                "score": 2.5,
                "feedback": "Good attempt but missed..."
            }}
            """
        else:
            # Zero-shot grading (No model answer)
            prompt = f"""
            You are an expert examiner. Grade this answer based on your general knowledge of the subject.
            
            Question: {q_text}
            Max Marks: {max_marks}
            
            Student Answer:
            {student_text}
            
            Task:
            1. Assign a score out of {max_marks}.
            2. Provide brief feedback.
            
            Output Format (JSON):
            {{
                "score": 2.5,
                "feedback": "Good attempt..."
            }}
            """
        
        try:
            response = self.gemini.generate_content(prompt)
            # Parse JSON (simple regex or assumption)
            import json
            # Clean markdown
            cleaned = response.replace("```json", "").replace("```", "").strip()
            if "{" in cleaned:
                cleaned = cleaned[cleaned.find("{"):cleaned.rfind("}")+1]
            
            data = json.loads(cleaned)
            
            score = float(data.get("score", 0))
            feedback = data.get("feedback", "")
            
            # Normalize to 0-1 ratio
            ratio = score / float(max_marks) if float(max_marks) > 0 else 0
            return ratio, feedback
            
        except Exception as e:
            logger.error(f"Grading failed: {e}")
            # Fallback if Gemini fails
            if model_text:
                return semantic_score, "Graded based on semantic similarity (AI fallback)."
            else:
                return 0.0, "Grading failed and no model answer available."

    def _generate_overall_feedback(self, total_score: Decimal, result_id: UUID) -> str:
        """
        Generates overall feedback using Gemini based on the total score and general performance.
        """
        try:
            # Fetch all question scores for this result to give a summary
            scores = self.db.query(QuestionScore).filter(QuestionScore.evaluation_result_id == result_id).all()
            
            summary_text = ""
            for s in scores:
                summary_text += f"- Q: {s.awarded_marks} marks. Feedback: {s.feedback}\n"
            
            prompt = f"""
            You are an expert examiner providing overall feedback for a student's exam paper.
            
            Total Score: {total_score}
            
            Question-wise Performance Summary:
            {summary_text[:5000]} (truncated if too long)
            
            Task:
            Provide a constructive overall feedback summary in Sinhala (or English if preferred by context).
            - Highlight strengths (answering style, good concepts).
            - Highlight general weaknesses or common mistakes found in the paper.
            - Provide encouragement.
            
            Keep it concise (2-3 paragraphs).
            """
            
            response = self.gemini.generate_content(prompt)
            return response.get("text", "").strip()
        except Exception as e:
            logger.error(f"Overall feedback generation failed: {e}")
            return f"Total Score: {total_score}. Good job!"

    def _generate_feedback_with_gemini(self, student_text: str, reference_text: str, question: Any, awarded_marks: Decimal, max_marks: int) -> str:
        """
        Generates detailed feedback using Gemini.
        """
        q_text = getattr(question, 'question_text', '') or getattr(question, 'sub_question_text', '')
        
        prompt = f"""
        You are an expert examiner. Provide feedback for this answer.
        
        Question: {q_text}
        Marks Awarded: {awarded_marks} / {max_marks}
        
        Student Answer:
        "{student_text}"
        
        Reference Material (Syllabus/Rubric Excerpt):
        "{reference_text}"
        
        Task:
        Provide constructive feedback in Sinhala (or English).
        1. Comment on the answering style.
        2. Identify missing concepts or key points based on the Reference Material.
        3. If the marks are low, explain why it is wrong or incomplete.
        4. Do NOT mention "Gemini" or "AI". Speak as a teacher.
        
        Keep it brief (2-3 sentences).
        """
        
        try:
            response = self.gemini.generate_content(prompt)
            return response.get("text", "").strip()
        except Exception as e:
            logger.error(f"Feedback generation failed: {e}")
            return "Feedback could not be generated."

