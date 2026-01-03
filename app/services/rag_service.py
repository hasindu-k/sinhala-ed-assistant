# app/services/rag_service.py
import logging
from typing import List, Dict, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.services.hybrid_retrieval_service import HybridRetrievalService
from app.services.resource_chunk_service import ResourceChunkService
from app.services.message_context_service import MessageContextService
from app.services.message_service import MessageService
from app.utils.sinhala_prompt_builder import build_qa_prompt, build_direct_answer_prompt
from app.utils.sinhala_summary_prompt_builder import build_summary_prompt
from app.utils.sinhala_safety_engine import concept_map_check, detect_misconceptions, attach_evidence
from app.services.message_safety_service import MessageSafetyService
from app.core.gemini_client import GeminiClient
import json
from app.services.intent_detection_service import IntentDetectionService
from app.services.answerability_service import AnswerabilityService

logger = logging.getLogger(__name__)


class RAGService:
    """RAG orchestration with hybrid retrieval, grounded generation, and safety checks."""

    def __init__(self, db: Session):
        self.db = db
        self.chunk_service = ResourceChunkService(db)
        self.context_service = MessageContextService(db)
        self.message_service = MessageService(db)
        self.safety_service = MessageSafetyService(db)

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
        if not AnswerabilityService.is_answerable(user_query, context):
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
            intent = IntentDetectionService.detect_intent(user_query)
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
                prompt = build_qa_prompt(
                    context=context,
                    count=5,
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
                    query=user_query
                )
                message_grade_level = None

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
        result = concept_map_check(generated, context)
        missing = result["missing_concepts"]
        extra = result["extra_concepts"]
        is_valid = len(missing) == 0 and len(extra) == 0

        flagged = detect_misconceptions(generated, context)
        flagged = attach_evidence(flagged, context)

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
        # 8. Save safety report
        # -----------------------------
        self.safety_service.create_safety_report(
            assistant_msg.id,
            {
                "missing_concepts": json.dumps(list(missing)[:50]) if missing else None,
                "extra_concepts": json.dumps(list(extra)[:50]) if extra else None,
                "flagged_sentences": json.dumps(flagged) if flagged else None,
                "reasoning": "Hybrid RAG with Sinhala QA/Summary",
            },
        )

        logger.info("Assistant message and safety report saved.")

        # -----------------------------
        # 9. Return full response with metadata
        # -----------------------------
        retrieval_metadata = {"bm25_k": bm25_k, "final_k": final_k, "used_chunks": len(hits)}

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
        }
