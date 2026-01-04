# app/services/intent_detection_service.py
from typing import Literal
import numpy as np
from app.components.document_processing.services.embedding_service import generate_text_embedding

IntentType = Literal[
    "greeting",
    "summary",
    "qa_generate",
    "qa_answer",
    "explanation",
]


class IntentDetectionService:
    """
    Option 3: Hybrid Rule + Semantic Gate
    """

    GREETING_RULES = ["hello", "hi", "hey", "හායි", "හලෝ", "ආයුබෝවන්", "කොහොමද", "ගුඩ් මෝනින්", "good morning", "good afternoon", "good evening"]
    SUMMARY_RULES = ["සාරාංශ", "සංක්ෂිප්ත", "කෙටියෙන්", "මුල් අදහස්"]
    QA_GENERATE_RULES = ["ප්‍රශ්න", "පිළිතුරු", "qa", "q&a", "සාදන්න", "හදන්න"]
    QA_ANSWER_RULES = ["යනු කුමක්ද", "කියන්න"]
    EXPLANATION_RULES = ["විස්තර", "පහදන්න", "පැහැදිලි"]

    SEMANTIC_ANCHORS = {
        "greeting": "හායි ආයුබෝවන් කොහොමද",
        "summary": "මෙම අන්තර්ගතය සාරාංශ කරන්න",
        "qa_generate": "මෙම පාඩමෙන් ප්‍රශ්න සහ පිළිතුරු සාදන්න",
        "qa_answer": "මෙම ප්‍රශ්නයට සෘජු පිළිතුරක් ලබා දෙන්න",
        "explanation": "මෙය විස්තර කර පැහැදිලි කරන්න",
    }

    @classmethod
    def detect_intent(cls, query: str) -> IntentType:
        q = query.lower().strip()

        # -------- Step 1: Rule-based --------
        # Check for greetings first (highest priority)
        if any(w in q for w in cls.GREETING_RULES):
            return "greeting"

        if any(w in q for w in cls.SUMMARY_RULES):
            return "summary"

        if any(w in q for w in cls.QA_GENERATE_RULES):
            return "qa_generate"

        if any(w in q for w in cls.EXPLANATION_RULES):
            return "explanation"

        if any(w in q for w in cls.QA_ANSWER_RULES) or q.endswith("?"):
            return "qa_answer"

        # -------- Step 2: Semantic gate --------
        query_vec = generate_text_embedding(query)
        if not query_vec:
            return "qa_answer"

        best_intent = "qa_answer"
        best_score = 0.0

        for intent, anchor in cls.SEMANTIC_ANCHORS.items():
            anchor_vec = generate_text_embedding(anchor)
            score = cls._cosine_similarity(query_vec, anchor_vec)

            if score > best_score:
                best_score = score
                best_intent = intent

        return best_intent if best_score >= 0.65 else "qa_answer"

    @staticmethod
    def _cosine_similarity(v1, v2):
        v1, v2 = np.array(v1), np.array(v2)
        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
