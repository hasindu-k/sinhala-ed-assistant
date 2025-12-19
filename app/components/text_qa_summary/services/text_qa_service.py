# app/components/text_qa_summary/services/text_qa_service.py
import uuid
import re
from typing import Tuple
from sqlalchemy.orm import Session
from app.shared.models.chat_messages import ChatMessage
from app.core.gemini_client import GeminiClient
from app.components.text_qa_summary.utils.prompts import build_qa_prompt, build_summary_prompt
from app.components.text_qa_summary.utils.safety import (
    concept_map_check, 
    detect_misconceptions, 
    adaptive_summary_clean,
    summary_fidelity_check,
    extract_key_concepts,
    hybrid_clean
)
from app.components.text_qa_summary.services.retrieval_service import RetrievalService


class TextQAService:
    @staticmethod
    def _save_message(
        db: Session,
        chat_id: uuid.UUID,
        user_id: str,
        role: str,
        prompt_original: str,
        prompt_cleaned: str,
        model_raw_output: str,
        final_output: str,
        safety_missing_concepts: list,
        safety_extra_concepts: list,
        safety_flagged_sentences: list
    ) -> ChatMessage:
        message = ChatMessage(
            id=uuid.uuid4(),
            chat_id=chat_id,
            user_id=user_id,
            role=role,
            prompt_original=prompt_original,
            prompt_cleaned=prompt_cleaned,
            model_raw_output=model_raw_output,
            final_output=final_output,
            safety_missing_concepts=safety_missing_concepts,
            safety_extra_concepts=safety_extra_concepts,
            safety_flagged_sentences=safety_flagged_sentences
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    @staticmethod
    def generate_qa(
        db: Session,
        chat_id: uuid.UUID,
        user_id: str,
        query: str,  # New parameter: user's query
        count: int
    ) -> Tuple[ChatMessage, dict]:
        print(f"[RAG] Generating Q&A for chat {chat_id}")
        print(f"[RAG] User query: {query}")
        
        # Step 1: Retrieve relevant chunks
        scored_chunks = RetrievalService.retrieve_relevant_chunks(
            db=db,
            chat_id=chat_id,
            query=query,
            top_k=15  # Retrieve more chunks for Q&A generation
        )
        
        if not scored_chunks:
            raise ValueError(f"No relevant content found for query: {query}")
        
        # Step 2: Generate context from retrieved chunks
        context, retrieval_metadata = RetrievalService.generate_context_from_chunks(
            scored_chunks
        )
        
        print(f"[RAG] Retrieved {retrieval_metadata['used_chunks']} chunks")
        print(f"[RAG] Average retrieval score: {retrieval_metadata['avg_score']:.3f}")
        
        # Step 3: Build prompt with retrieved context
        prompt = build_qa_prompt(context, count, query)
        
        # Step 4: Generate from Gemini
        raw_output = GeminiClient.generate_content(prompt)
        
        # Step 5: Safety checks
        is_valid, missing, extra = concept_map_check(raw_output, context)
        flagged = detect_misconceptions(raw_output, context)
        
        # Step 6: Clean output
        final_output = hybrid_clean(raw_output, flagged)
        
        # Step 7: Save to database with retrieval metadata
        message = TextQAService._save_message(
            db=db,
            chat_id=chat_id,
            user_id=user_id,
            role="assistant",
            prompt_original=prompt,
            prompt_cleaned=prompt,
            model_raw_output=raw_output,
            final_output=final_output,
            safety_missing_concepts=missing,
            safety_extra_concepts=extra,
            safety_flagged_sentences=flagged
        )
        
        # Enhanced safety checks with retrieval info
        safety_checks = {
            "is_valid": is_valid,
            "missing_concepts": missing,
            "extra_concepts": extra,
            "flagged_sentences": flagged,
            "total_missing": len(missing),
            "total_extra": len(extra),
            "total_flagged": len(flagged),
            "retrieval_metadata": retrieval_metadata
        }
        
        return message, safety_checks

    @staticmethod
    def generate_summary(
        db: Session,
        chat_id: uuid.UUID,
        user_id: str,
        query: str,
        grade: str
    ) -> Tuple[ChatMessage, dict]:
        print(f"[RAG] Generating ADAPTIVE summary for grade {grade}")
        print(f"[RAG] User query: {query}")
        
        # Step 1: Retrieve relevant chunks
        scored_chunks = RetrievalService.retrieve_relevant_chunks(
            db=db,
            chat_id=chat_id,
            query=query,
            top_k=10
        )
        
        if not scored_chunks:
            raise ValueError(f"No relevant content found for query: {query}")
        
        # Step 2: Generate context from retrieved chunks
        context, retrieval_metadata = RetrievalService.generate_context_from_chunks(
            scored_chunks
        )
        
        print(f"[RAG] Retrieved {retrieval_metadata['used_chunks']} chunks")
        print(f"[RAG] Average retrieval score: {retrieval_metadata['avg_score']:.3f}")
        print(f"[RAG] Source context length: {len(context)} characters")
        
        # Extract key concepts for logging
        key_concepts = extract_key_concepts(context, top_n=10)
        print(f"[RAG] Key concepts in source: {key_concepts}")
        
        # Step 3: Build grade-specific prompt
        prompt = build_summary_prompt(context, grade, query)
        
        # Step 4: Generate from Gemini
        raw_output = GeminiClient.generate_content(prompt)
        print(f"[RAG] Raw summary length: {len(raw_output)} characters")
        
        # Step 5: Summary fidelity check (NEW - better than concept_map_check)
        fidelity_check = summary_fidelity_check(raw_output, context, grade)
        
        # Step 6: Detect hallucinations
        flagged = detect_misconceptions(raw_output, context, grade)
        
        # Step 7: Adaptive cleaning - preserves important content
        final_output = adaptive_summary_clean(raw_output, context, flagged, grade)
        
        # Step 8: Log what was preserved/missing
        print(f"[SUMMARY] Grade {grade} - Key concept preservation:")
        print(f"  - Target: {fidelity_check['preservation_target']:.0%}")
        print(f"  - Achieved: {fidelity_check['preservation_ratio']:.0%}")
        print(f"  - Meets target: {fidelity_check['meets_preservation_target']}")
        
        if not fidelity_check['meets_preservation_target']:
            print(f"  - Missing key concepts: {fidelity_check['missing_key_concepts'][:5]}")
        
        # Step 9: Save to database
        # For backward compatibility, still use concept_map_check results
        _, missing, extra = concept_map_check(raw_output, context, grade)
        
        message = TextQAService._save_message(
            db=db,
            chat_id=chat_id,
            user_id=user_id,
            role="teacher",
            prompt_original=prompt,
            prompt_cleaned=prompt,
            model_raw_output=raw_output,
            final_output=final_output,
            safety_missing_concepts=missing,
            safety_extra_concepts=extra,
            safety_flagged_sentences=flagged
        )
        
        # Comprehensive safety checks
        safety_checks = {
            "is_valid": fidelity_check["is_valid_summary"],
            "fidelity_check": fidelity_check,
            "flagged_sentences_count": len(flagged),
            "retrieval_metadata": {
                "chunks_retrieved": retrieval_metadata.get("used_chunks", 0),
                "avg_score": retrieval_metadata.get("avg_score", 0),
                "total_chunks_available": retrieval_metadata.get("total_chunks", 0)
            },
            "content_analysis": {
                "source_length": len(context),
                "summary_length": len(final_output),
                "compression_ratio": round(len(final_output) / len(context), 2) if context else 0,
                "grade_level": grade
            }
        }
        
        return message, safety_checks

    @staticmethod
    def get_chat_messages(db: Session, chat_id: uuid.UUID) -> list[ChatMessage]:
        return db.query(ChatMessage).filter(
            ChatMessage.chat_id == chat_id
        ).order_by(ChatMessage.created_at).all()