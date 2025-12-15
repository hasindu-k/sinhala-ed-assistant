# app/components/text_qa_summary/services/text_qa_service.py
import uuid
from typing import Tuple
from sqlalchemy.orm import Session
from app.shared.models.chat_messages import ChatMessage
from app.core.gemini_client import GeminiClient
from app.components.text_qa_summary.utils.prompts import build_qa_prompt, build_summary_prompt
from app.components.text_qa_summary.utils.safety import (
    concept_map_check, detect_misconceptions, hybrid_clean
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
            role="teacher",
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
        query: str,  # New parameter: user's query
        grade: str
    ) -> Tuple[ChatMessage, dict]:
        print(f"[RAG] Generating summary for chat {chat_id}")
        print(f"[RAG] User query: {query}")
        print(f"[RAG] Grade level: {grade}")
        
        # Step 1: Retrieve relevant chunks
        scored_chunks = RetrievalService.retrieve_relevant_chunks(
            db=db,
            chat_id=chat_id,
            query=query,
            top_k=10  # Fewer chunks for summary
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
        prompt = build_summary_prompt(context, grade, query)
        
        # Step 4: Generate from Gemini
        raw_output = GeminiClient.generate_content(prompt)
        
        # Step 5: Safety checks
        is_valid, missing, extra = concept_map_check(raw_output, context)
        flagged = detect_misconceptions(raw_output, context)
        
        # Step 6: Clean output
        final_output = hybrid_clean(raw_output, flagged)
        
        # Step 7: Save to database
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
    def get_chat_messages(db: Session, chat_id: uuid.UUID) -> list[ChatMessage]:
        return db.query(ChatMessage).filter(
            ChatMessage.chat_id == chat_id
        ).order_by(ChatMessage.created_at).all()