# app/services/answerability_service.py
import re
from typing import List

class AnswerabilityService:
    """
    Determines whether a question can be answered
    using the retrieved context only.
    """

    @staticmethod
    def extract_key_terms(question: str) -> List[str]:
        """
        Extract Sinhala content words (simple, safe).
        """
        tokens = re.findall(r"[අ-෴]+", question)
        stopwords = {
            "යනු", "කුමක්ද", "ද", "මොනවාද", "පිළිබඳ",
            "කරුණාකර", "පැහැදිලි", "කරන්න"
        }
        return [t for t in tokens if t not in stopwords and len(t) > 2]

    @staticmethod
    def is_answerable(question: str, context: str) -> bool:
        """
        A question is answerable if at least one key term
        appears in the retrieved context.
        """
        key_terms = AnswerabilityService.extract_key_terms(question)

        if not key_terms:
            return True  # fallback safe

        context_lower = context.lower()
        hits = sum(1 for t in key_terms if t.lower() in context_lower)

        # require at least one strong overlap
        return hits > 0
