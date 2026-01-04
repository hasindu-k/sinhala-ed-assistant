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
            return None

        # If summary was pre-computed and cached, return it immediately (fast path)
        if (hasattr(report, 'computed_severity') and report.computed_severity and 
            hasattr(report, 'computed_confidence_score') and report.computed_confidence_score is not None and
            hasattr(report, 'computed_reliability') and report.computed_reliability):
            return {
                "overall_severity": report.computed_severity,
                "confidence_score": report.computed_confidence_score,
                "reliability": report.computed_reliability,
                "message": self._summary_message(report.computed_severity, report.computed_confidence_score),
                "has_details": report.computed_severity != "low",
                "flags": {"flagged_sentences": len(report.flagged_sentences or [])},
            }

        # Fallback: compute on demand if not cached (backward compatibility)
        flagged = report.flagged_sentences or []

        if not flagged:
            return {
                "overall_severity": "low",
                "confidence_score": 1.0,
                "reliability": "fully_supported",
                "message": "This answer is well supported by the provided content.",
                "has_details": False,
                "flags": {"flagged_sentences": 0},
            }

        # -----------------------------
        # Sentence-level semantic check (BATCH)
        # -----------------------------
        # Prepare pairs for batch processing
        pairs = [(item.get("sentence", ""), item.get("evidence", "")) for item in flagged]
        
        # Batch compute all similarities at once (MUCH faster)
        similarities = SemanticSimilarityService.similarity_batch(pairs)
        
        severities = []
        for similarity in similarities:
            if similarity >= 0.80:
                severities.append("low")
            elif similarity >= 0.65:
                severities.append("medium")
            else:
                severities.append("high")

        total = len(severities)
        high_count = severities.count("high")
        medium_count = severities.count("medium")

        high_ratio = high_count / total
        medium_plus_ratio = (high_count + medium_count) / total

        # -----------------------------
        # Overall severity (PROPORTIONAL)
        # -----------------------------
        if high_ratio >= 0.30:
            overall_severity = "high"
        elif medium_plus_ratio >= 0.40:
            overall_severity = "medium"
        else:
            overall_severity = "low"

        # -----------------------------
        # Confidence score (semantic)
        # -----------------------------
        avg_similarity = sum(similarities) / total
        confidence_score = round(avg_similarity, 2)

        # -----------------------------
        # Reliability (aligned)
        # -----------------------------
        if confidence_score >= 0.85:
            reliability = "fully_supported"
        elif confidence_score >= 0.65:
            reliability = "partially_supported"
        else:
            reliability = "likely_unsupported"

        # -----------------------------
        # User-facing message
        # -----------------------------
        message = self._summary_message(
            overall_severity, confidence_score
        )

        return {
            "overall_severity": overall_severity,
            "confidence_score": confidence_score,
            "reliability": reliability,
            "message": message,
            "has_details": overall_severity != "low",
            "flags": {
                "flagged_sentences": total,
            },
        }

    def _summary_message(self, severity: str, confidence: float) -> str:
        if severity == "high":
            return (
                "Some parts of this answer are not clearly supported "
                "by the provided content."
            )
        if severity == "medium":
            return (
                "Most of this answer is supported, but a few parts "
                "may need verification."
            )
        return "This answer is well supported by the provided content."

    @staticmethod
    def compute_from_flagged(flagged: list, is_unanswerable: bool = False) -> dict:
        """Compute summary values from flagged sentences (for caching at creation time)"""
        if is_unanswerable or not flagged:
            # Clean response or unanswerable
            return {
                "computed_severity": "low",
                "computed_confidence_score": 1.0,
                "computed_reliability": "fully_supported",
            }
        
        # Compute summary once here
        pairs = [(item.get("sentence", ""), item.get("evidence", "")) for item in flagged[:10]]
        similarities = SemanticSimilarityService.similarity_batch(pairs)
        
        severities = []
        for similarity in similarities:
            if similarity >= 0.80:
                severities.append("low")
            elif similarity >= 0.65:
                severities.append("medium")
            else:
                severities.append("high")
        
        total = len(severities)
        high_count = severities.count("high")
        medium_count = severities.count("medium")
        high_ratio = high_count / total if total > 0 else 0
        medium_plus_ratio = (high_count + medium_count) / total if total > 0 else 0
        
        if high_ratio >= 0.30:
            computed_severity = "high"
        elif medium_plus_ratio >= 0.40:
            computed_severity = "medium"
        else:
            computed_severity = "low"
        
        avg_similarity = sum(similarities) / total if total > 0 else 1.0
        computed_confidence = round(avg_similarity, 2)
        
        if computed_confidence >= 0.85:
            computed_reliability = "fully_supported"
        elif computed_confidence >= 0.65:
            computed_reliability = "partially_supported"
        else:
            computed_reliability = "likely_unsupported"
        
        return {
            "computed_severity": computed_severity,
            "computed_confidence_score": computed_confidence,
            "computed_reliability": computed_reliability,
        }