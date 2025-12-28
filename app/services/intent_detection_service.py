# app/services/intent_detection_service.py

from typing import Literal
import numpy as np
from app.components.document_processing.services.embedding_service import generate_text_embedding

IntentType = Literal["summary", "qa", "explanation", "answer"]


class IntentDetectionService:
    """
    Option 3: Hybrid Rule + Semantic Gate
    """

    SUMMARY_RULES = ["සාරාංශ", "සංක්ෂිප්ත", "කෙටියෙන්", "මුල් අදහස්"]
    QA_RULES = ["ප්‍රශ්න", "පිළිතුරු", "qa", "q&a"]
    EXPLANATION_RULES = ["විස්තර", "පහදන්න", "පැහැදිලි"]

    SEMANTIC_ANCHORS = {
        "summary": "මෙම අන්තර්ගතය සාරාංශ කරන්න",
        "qa": "මෙම පාඩමෙන් ප්‍රශ්න සහ පිළිතුරු සාදන්න",
        "explanation": "මෙය විස්තර කර පැහැදිලි කරන්න",
    }

    @classmethod
    def detect_intent(cls, query: str) -> IntentType:
        q = query.lower()

        # -------- Step 1: Rule-based (deterministic) --------
        if any(w in q for w in cls.SUMMARY_RULES):
            return "summary"

        if any(w in q for w in cls.QA_RULES):
            return "qa"

        if any(w in q for w in cls.EXPLANATION_RULES):
            return "explanation"

        # -------- Step 2: Semantic gate (embedding similarity) --------
        query_vec = generate_text_embedding(query)
        if not query_vec:
            return "answer"

        best_intent = "answer"
        best_score = 0.0

        for intent, anchor in cls.SEMANTIC_ANCHORS.items():
            anchor_vec = generate_text_embedding(anchor)
            score = cls._cosine_similarity(query_vec, anchor_vec)

            if score > best_score:
                best_score = score
                best_intent = intent

        # Confidence threshold
        return best_intent if best_score >= 0.65 else "answer"

    @staticmethod
    def _cosine_similarity(v1, v2):
        v1, v2 = np.array(v1), np.array(v2)
        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
