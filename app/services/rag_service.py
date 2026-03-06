# app/services/rag_service.py
import logging
from typing import List, Dict, Optional
from uuid import UUID
from sqlalchemy.orm import Session
import re 

from app.services.hybrid_retrieval_service import HybridRetrievalService
from app.services.resource_chunk_service import ResourceChunkService
from app.services.message_context_service import MessageContextService
from app.services.message_service import MessageService
from app.utils.sinhala_prompt_builder import build_qa_prompt, build_direct_answer_prompt
from app.utils.sinhala_summary_prompt_builder import build_summary_prompt
from app.utils.sinhala_safety_engine import concept_map_check, detect_misconceptions, attach_evidence
from app.services.message_safety_service import MessageSafetyService
from app.core.gemini_client import GeminiClient
from app.services.intent_detection_service import IntentDetectionService
from app.services.answerability_service import AnswerabilityService
from app.services.xai_service import XAIService

logger = logging.getLogger(__name__)


class RAGService:
    """RAG orchestration with hybrid retrieval, grounded generation, and safety checks."""
    GREETING_ONLY = ["hello", "hi", "hey", "හායි", "හලෝ", "ආයුබෝවන්", "කොහොමද", "ගුඩ් මෝනින්", "good morning", "good afternoon", "good evening"] 

    def __init__(self, db: Session):
        self.db = db
        self.chunk_service = ResourceChunkService(db)
        self.context_service = MessageContextService(db)
        self.message_service = MessageService(db)
        self.safety_service = MessageSafetyService(db)

    def extract_question_count(query: str) -> int:
        match = re.search(r"\d+", query)
        if match:
            return int(match.group())
        return 5

    def generate_response(
        self,
        session_id: UUID,
        user_message_id: UUID,
        user_query: str,
        resource_ids: List[UUID],
        query_embedding: Optional[List[float]] = None,
        bm25_k: int = 20,
        final_k: int = 8,
        grade_level: Optional[str] = None,
    ) -> Dict:
        """Hybrid retrieval → grounded generation → safety checks → logging"""

        # cleaned = user_query.lower().strip()

        # if not resource_ids and cleaned in self.GREETING_ONLY:
        #     greeting_text = "ආයුබෝවන්! මට ඔබට උදව් කළ හැකිය. කරුණාකර ඔබගේ ප්‍රශ්නය අසන්න."
        #     assistant_msg = self.message_service.create_assistant_message(
        #         session_id=session_id,
        #         content=greeting_text,
        #         model_info={"model_name": "rule-based"},
        #         parent_msg_id=user_message_id
        #     )
        #     logger.info("Greeting detected, returning simple response without RAG")
        #     return {
        #         "assistant_message_id": assistant_msg.id,
        #         "content": greeting_text,
        #         "sources": [],
        #         "retrieval_metadata": {"intent": "greeting", "used_chunks": 0},
        #     }

        # -----------------------------
        # 0. Check for greetings/chit-chat (no RAG needed)
        # -----------------------------

        def extract_question_count(query: str) -> int:
            match = re.search(r"\d+", query)
            if match:
                return int(match.group())
            return 5
        
        intent = IntentDetectionService.detect_intent(user_query)

        if intent == "greeting":
            greeting_text = "ආයුබෝවන්! මට ඔබට උදව් කළ හැකිය. කරුණාකර ඔබගේ ප්‍රශ්නය අසන්න."

            assistant_msg = self.message_service.create_assistant_message(
                session_id=session_id,
                content=greeting_text,
                model_info={"model_name": "rule-based"},
                parent_msg_id=user_message_id
            )

            logger.info("Greeting detected early — skipping RAG pipeline")

            return {
                "assistant_message_id": assistant_msg.id,
                "content": greeting_text,
                "sources": [],
                "retrieval_metadata": {"intent": "greeting", "used_chunks": 0},
            }

        # if intent == "greeting":
        #     greeting_text = "ආයුබෝවන්! මට ඔබට උදව් කළ හැකිය. කරුණාකර ඔබගේ ප්‍රශ්නය අසන්න."
        #     assistant_msg = self.message_service.create_assistant_message(
        #         session_id=session_id,
        #         content=greeting_text,
        #         model_info={"model_name": "rule-based"},
        #         parent_msg_id=user_message_id
        #     )
        #     logger.info("Greeting detected, returning simple response without RAG")
        #     return {
        #         "assistant_message_id": assistant_msg.id,
        #         "content": greeting_text,
        #         "sources": [],
        #         "retrieval_metadata": {"intent": "greeting", "used_chunks": 0},
        #     }

        if not query_embedding:
            raise ValueError("Query embedding is required for hybrid retrieval")

        # -----------------------------
        # 1. Hybrid retrieval
        # -----------------------------
        hybrid_service = HybridRetrievalService(self.db)
        hits = hybrid_service.retrieve(
            resource_ids=resource_ids,
            query=user_query,
            query_embedding=query_embedding,
            bm25_k=bm25_k,
            final_k=final_k,
        )

        if not hits:
            # Zero-hallucination refusal
            refusal_text = "මෙම ප්‍රශ්නයට අදාල තොරතුරු ලබා දී ඇති අන්තර්ගතයේ නොමැත."
            assistant_msg = self.message_service.create_assistant_message(
                session_id=session_id,
                content=refusal_text,
                model_info={"model_name": "gemini-3-flash-preview"},
                parent_msg_id=user_message_id
            )
            return {
                "assistant_message_id": assistant_msg.id,
                "content": refusal_text,
                "sources": [],
                "retrieval_metadata": {"bm25_k": bm25_k, "final_k": final_k, "used_chunks": 0},
            }

        logging.info("Hybrid retrieval returned %d hits", len(hits))

        # -----------------------------
        # 2. Log used chunks
        # -----------------------------
        self.context_service.log_used_chunks(
            user_message_id,
            [
                {
                    "chunk_id": h["id"],
                    "similarity_score": h.get("similarity"),
                    "rank": i + 1,
                }
                for i, h in enumerate(hits)
            ],
        )

        # -----------------------------
        # 3. Build context
        # -----------------------------
        context = "\n\n".join(h["content"] for h in hits)

        logger.info("Built context of length %d", len(context))

        # -----------------------------
        # ANSWERABILITY GUARD (CRITICAL)
        # -----------------------------
        if intent in ["summary", "qa_generate", "qa_answer", "explanation"]:
            is_unanswerable = False
        else:
            is_unanswerable = not AnswerabilityService.is_answerable(user_query, context)
        
        if is_unanswerable:
            logger.warning("Unanswerable question detected: %s", user_query)

            refusal_prompt = f"""
        ඔබට ලබා දී ඇති අන්තර්ගතය තුළ
        "{user_query}" පිළිබඳ පැහැදිලි තොරතුරු නොමැත.

        🔒 නියම:
        • ලබා දී ඇති අන්තර්ගතයෙන් පිටත කරුණු එකතු නොකරන්න
        • නිගමන හෝ අනුමාන නොකරන්න

        📚 ලබා දී ඇති අන්තර්ගතය:
        {context}

        ✍️ පිළිතුර:
        """

            prompt = refusal_prompt
            message_grade_level = None

            # Skip normal intent routing
        else:
            # -----------------------------
            # 4. Select prompt type
            # -----------------------------
            # Re-use intent from earlier or re-detect
            logger.info("Detected intent: %s", intent)

            # 🟢 Summary
            if intent == "summary":
                prompt = build_summary_prompt(
                    context=context,
                    grade_level=grade_level,
                    query=user_query
                )
                message_grade_level = grade_level

            # 🟢 Q&A GENERATION (lesson practice)
            elif intent == "qa_generate":

                count = extract_question_count(user_query)

                # limit range for safety
                count = max(1, min(count, 10))

                prompt = build_qa_prompt(
                    context=context,
                    count=count,
                    query=user_query
                )

                message_grade_level = None

            # 🟢 DIRECT ANSWER (NEW)
            elif intent == "qa_answer":
                prompt = build_direct_answer_prompt(
                    context=context,
                    query=user_query
                )
                message_grade_level = None

            # 🟡 Explanation fallback
            elif intent == "explanation":
                prompt = build_direct_answer_prompt(
                    context=context,
                    query=user_query,
                    grade=grade_level,
                )
                message_grade_level = grade_level

            # 🔴 Safe fallback
            else:
                prompt = build_direct_answer_prompt(
                    context=context,
                    query=user_query
                )
                message_grade_level = None



        # -----------------------------
        # 5. Generate response with Gemini
        # -----------------------------
        generated_result  = GeminiClient.generate_content(prompt)
        generated = generated_result["text"]
        prompt_tokens = generated_result["prompt_tokens"]
        completion_tokens = generated_result["completion_tokens"]
        total_tokens = generated_result["total_tokens"]

        logger.info("Generated response of length %d", len(generated))

        # -----------------------------
        # 6. Safety & misconception checks
        # -----------------------------
        # Skip safety checks for legitimate "information not found" responses
        if is_unanswerable:
            logger.info("Skipping safety checks for unanswerable question (legitimate refusal)")
            missing = set()
            extra = set()
            is_valid = True
            flagged = []
        else:
            result = concept_map_check(generated, context)
            missing = result["missing_concepts"]
            extra = result["extra_concepts"]
            is_valid = len(missing) == 0 and len(extra) == 0

            flagged = detect_misconceptions(generated, context)
            logging.info("Detected %d flagged misconceptions", len(flagged))
            flagged = attach_evidence(flagged, context)
            logging.info("Attached evidence to flagged misconceptions")
            

            # ---- High-level summary ----
            logger.info(
                "Safety check summary | is_valid=%s | missing=%d | extra=%d | flagged=%d",
                is_valid,
                len(missing),
                len(extra),
                len(flagged),
            )

            # ---- Detailed concept logs ----
            if missing:
                logger.info("Missing concepts: %s", missing[:15])  # limit for readability

            if extra:
                logger.info("Extra concepts: %s", extra[:15])

            # ---- Detailed misconception logs ----
            for i, f in enumerate(flagged, start=1):
                logger.info(
                    "FLAGGED #%d | severity=%s | ratio=%.2f\nSENTENCE: %s\nEVIDENCE: %s",
                    i,
                    f.get("severity"),
                    f.get("unseen_ratio"),
                    f.get("sentence"),
                    f.get("evidence"),
                )

        logger.info("Saving assistant message...")

        # -----------------------------
        # 7. Save assistant message
        # -----------------------------
        
        assistant_msg = self.message_service.create_assistant_message(
            session_id=session_id,
            content=generated,
            model_info={
                "model_name": "gemini-3-flash-preview", 
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
                },
            grade_level=message_grade_level,
            parent_msg_id=user_message_id
        )

        # -----------------------------
        # 8. Compute summary and save safety report
        # -----------------------------
        # Pre-compute and cache the summary to avoid recalculation on every fetch
        from app.services.safety_summary_service import SafetySummaryService
        
        computed_values = SafetySummaryService.compute_from_flagged(flagged, is_unanswerable)

        # Build retrieval metadata for XAI generation
        retrieval_metadata = {"bm25_k": bm25_k, "final_k": final_k, "used_chunks": len(hits)}

        # Generate XAI explanation BEFORE saving so it gets persisted with the safety report
        xai_explanation = XAIService.generate_explanation(
            user_query=user_query,
            generated_answer=generated,
            retrieved_chunks=hits,
            safety_report={
                "flagged": flagged,
                "missing_concepts": list(missing),
                "extra_concepts": list(extra),
                "confidence_score": computed_values.get("computed_confidence_score", 1.0) if not is_unanswerable else 1.0,
            } if not is_unanswerable else None,
            retrieval_metadata=retrieval_metadata,
        )

        self.safety_service.create_safety_report(
            assistant_msg.id,
            {
                "missing_concepts": list(missing)[:50] if missing else None,
                "extra_concepts": list(extra)[:50] if extra else None,
                "flagged_sentences": flagged if flagged else None,
                "reasoning": "Hybrid RAG with Sinhala QA/Summary",
                # Cache computed values
                **computed_values,
                "xai_explanation": xai_explanation,
            },
        )

        logger.info("Assistant message and safety report saved.")

        # -----------------------------
        # 9. Return full response with metadata
        # -----------------------------
        retrieval_metadata = {"bm25_k": bm25_k, "final_k": final_k, "used_chunks": len(hits)}

        # Generate XAI explanation
        xai_explanation = XAIService.generate_explanation(
            user_query=user_query,
            generated_answer=generated,
            retrieved_chunks=hits,
            safety_report={
                "flagged": flagged,
                "missing_concepts": list(missing),
                "extra_concepts": list(extra),
                "confidence_score": computed_values.get("computed_confidence_score", 1.0) if not is_unanswerable else 1.0
            } if not is_unanswerable else None,
            retrieval_metadata=retrieval_metadata
        )

        return {
            "assistant_message_id": assistant_msg.id,
            "content": generated,
            "sources": hits,
            "retrieval_metadata": retrieval_metadata,
            "safety": {
                "is_valid": is_valid,
                "missing_concepts": list(missing)[:10],
                "extra_concepts": list(extra)[:10],
                "flagged": flagged,
            },
            "xai_explanation": xai_explanation
        }
