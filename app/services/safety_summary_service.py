from typing import Dict
from uuid import UUID

from app.services.message_safety_service import MessageSafetyService


class SafetySummaryService:
    """
    Builds a lightweight, user-facing safety summary derived from
    the detailed MessageSafetyReport.

    This service does NOT persist data.
    It only aggregates and interprets existing safety analysis.
    """

    # Tunable heuristics (documented for explainability)
    MAX_PENALTY = 50
    FLAG_WEIGHT = 2  # flagged sentences are higher risk than concept mismatches

    def __init__(self, db):
        self.safety_service = MessageSafetyService(db)

    def build_summary(self, message_id: UUID) -> Dict:
        report = self.safety_service.get_safety_report(message_id)

        # No safety analysis yet
        if not report:
            return self._empty_summary()

        flagged = report.flagged_sentences or []
        missing = report.missing_concepts or []
        extra = report.extra_concepts or []

        severity = self._compute_severity(flagged, missing, extra)
        confidence = self._compute_confidence(missing, extra, flagged)
        reliability = self._reliability_label(confidence)

        return {
            "severity": severity,
            "confidence": confidence,
            "reliability": reliability,
            "explanation": self._summary_message(severity),
            "has_details": bool(missing or extra or flagged),
            "has_high_risk": severity == "high",
            "counts": {
                "missing": len(missing),
                "extra": len(extra),
                "flagged": len(flagged),
            },
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_severity(self, flagged, missing, extra) -> str:
        """
        Severity prioritizes correctness risk over quantity.
        """
        if any(f.get("severity") == "high" for f in flagged):
            return "high"

        if flagged or len(missing) > 5 or len(extra) > 5:
            return "medium"

        return "low"

    def _compute_confidence(self, missing, extra, flagged) -> float:
        """
        Confidence reflects how much of the answer is supported
        by retrieved content.
        """
        penalty = (
            len(missing)
            + len(extra)
            + (len(flagged) * self.FLAG_WEIGHT)
        )

        score = max(0.0, 1.0 - (penalty / self.MAX_PENALTY))
        return round(score, 2)

    def _reliability_label(self, confidence: float) -> str:
        if confidence >= 0.85:
            return "fully_supported"
        if confidence >= 0.6:
            return "partially_supported"
        return "likely_unsupported"

    def _summary_message(self, severity: str) -> str:
        if severity == "high":
            return "This answer contains information not supported by the provided content."
        if severity == "medium":
            return "Some parts of this answer may not be fully supported."
        return "This answer is well supported by the provided content."

    def _empty_summary(self) -> Dict:
        return {
            "severity": "low",
            "confidence": 1.0,
            "reliability": "fully_supported",
            "explanation": "No safety issues detected.",
            "has_details": False,
            "has_high_risk": False,
            "counts": {
                "missing": 0,
                "extra": 0,
                "flagged": 0,
            },
        }
