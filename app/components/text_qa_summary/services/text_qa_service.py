# app/components/text_qa_summary/services/text_qa_service.py
import uuid
from typing import Tuple
from sqlalchemy.orm import Session
from app.shared.models.chat_messages import ChatMessage
from app.shared.ai.gemini_client import gemini_generate
from app.components.text_qa_summary.utils.prompts import build_qa_prompt, build_summary_prompt
from app.components.text_qa_summary.utils.safety import (
    concept_map_check, detect_misconceptions, hybrid_clean
)


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
        combined_text: str,
        count: int
    ) -> Tuple[ChatMessage, dict]:
        # Build prompt
        prompt = build_qa_prompt(combined_text, count)
        
        # Generate from Gemini
        raw_output = gemini_generate(prompt)
        
        # Safety checks
        is_valid, missing, extra = concept_map_check(raw_output, combined_text)
        flagged = detect_misconceptions(raw_output, combined_text)
        
        # Clean output
        final_output = hybrid_clean(raw_output, flagged)
        
        # Save to database
        message = TextQAService._save_message(
            db=db,
            chat_id=chat_id,
            user_id=user_id,
            role="teacher",
            prompt_original=prompt,
            prompt_cleaned=prompt,  # No cleaning applied to prompt in this version
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
            "total_flagged": len(flagged)
        }
        
        return message, safety_checks

    @staticmethod
    def generate_summary(
        db: Session,
        chat_id: uuid.UUID,
        user_id: str,
        combined_text: str,
        grade: str
    ) -> Tuple[ChatMessage, dict]:
        # Build prompt
        prompt = build_summary_prompt(combined_text, grade)
        
        # Generate from Gemini
        raw_output = gemini_generate(prompt)
        
        # Safety checks
        is_valid, missing, extra = concept_map_check(raw_output, combined_text)
        flagged = detect_misconceptions(raw_output, combined_text)
        
        # Clean output
        final_output = hybrid_clean(raw_output, flagged)
        
        # Save to database
        message = TextQAService._save_message(
            db=db,
            chat_id=chat_id,
            user_id=user_id,
            role="teacher",
            prompt_original=prompt,
            prompt_cleaned=prompt,  # No cleaning applied to prompt in this version
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
            "total_flagged": len(flagged)
        }
        
        return message, safety_checks

    @staticmethod
    def get_chat_messages(db: Session, chat_id: uuid.UUID) -> list[ChatMessage]:
        return db.query(ChatMessage).filter(
            ChatMessage.chat_id == chat_id
        ).order_by(ChatMessage.created_at).all()