from typing import Dict
from app.services.message_safety_service import MessageSafetyService
import logging
logger = logging.getLogger(__name__)
from app.services.semantic_similarity_service import SemanticSimilarityService


class SafetySummaryService:
    def __init__(self, db):
        self.safety_service = MessageSafetyService(db)

    def build_summary(self, message_id) -> Dict:
        report = self.safety_service.get_safety_report(message_id)

        if not report:
            return {
                "overall_severity": "low",
                "confidence_score": 1.0,
                "reliability": "fully_supported",
                "flags": {},
                "message": "This answer is well supported by the provided content.",
                "has_details": False,
            }

        flagged = report.flagged_sentences or []

        # -----------------------------
        # Re-evaluate severity using SEMANTIC similarity
        # -----------------------------
        semantic_severities = []
        similarity_scores = []

        for item in flagged:
            sentence = item.get("sentence", "")
            evidence = item.get("evidence", "")

            similarity = SemanticSimilarityService.similarity(
                sentence, evidence
            )
            similarity_scores.append(similarity)

            if similarity >= 0.80:
                semantic_severities.append("low")
            elif similarity >= 0.65:
                semantic_severities.append("medium")
            else:
                semantic_severities.append("high")

        # -----------------------------
        # Overall severity (semantic-based)
        # -----------------------------
        if "high" in semantic_severities:
            overall = "high"
        elif semantic_severities.count("medium") >= 2:
            overall = "medium"
        else:
            overall = "low"

        # -----------------------------
        # Confidence score (meaning-based)
        # -----------------------------
        if similarity_scores:
            avg_similarity = sum(similarity_scores) / len(similarity_scores)
        else:
            avg_similarity = 1.0

        # Convert similarity → confidence
        confidence = max(0.05, round(avg_similarity, 2))

        # -----------------------------
        # Reliability label
        # -----------------------------
        if confidence >= 0.85:
            reliability = "fully_supported"
        elif confidence >= 0.65:
            reliability = "partially_supported"
        else:
            reliability = "likely_unsupported"

        return {
            "overall_severity": overall,
            "confidence_score": confidence,
            "reliability": reliability,
            "flags": {
                "flagged_sentences": len(flagged),
            },
            "message": self._summary_message(overall),
            "has_details": overall != "low",
        }

    def _summary_message(self, severity: str) -> str:
        if severity == "high":
            return "This answer contains information not supported by the provided content."
        if severity == "medium":
            return "Some parts of this answer may not be fully supported."
        return "This answer is well supported by the provided content."
