import logging
from dataclasses import dataclass

from app.core.config import settings
from app.core.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GeminiDutyBudget:
    duty_name: str
    request_budget: int


class EvaluationGeminiClient:
    """Budget-aware Gemini wrapper for evaluation-mode duties."""

    OCR_CORRECTION = GeminiDutyBudget(
        duty_name="ocr_correction",
        request_budget=settings.EVAL_GEMINI_OCR_CORRECTION_MAX_REQUESTS,
    )
    ANSWER_MAPPING = GeminiDutyBudget(
        duty_name="answer_mapping",
        request_budget=settings.EVAL_GEMINI_ANSWER_MAPPING_MAX_REQUESTS,
    )
    REFERENCE_SCHEMA = GeminiDutyBudget(
        duty_name="reference_extraction",
        request_budget=settings.EVAL_GEMINI_REFERENCE_SCHEMA_MAX_REQUESTS,
    )

    @classmethod
    def generate_once(
        cls,
        prompt: str,
        *,
        budget: GeminiDutyBudget,
        json_mode: bool = False,
        reason: str | None = None,
    ) -> str:
        if not prompt or not prompt.strip():
            return ""

        requests_used = 1
        fallback_used = False
        log_reason = reason or "primary"

        logger.info(
            "[EVAL_GEMINI] duty_name=%s request_budget=%s requests_used=%s fallback_used=%s reason=%s",
            budget.duty_name,
            budget.request_budget,
            requests_used,
            fallback_used,
            log_reason,
        )

        try:
            result = GeminiClient.generate_content(
                prompt,
                max_retries=0,
                json_mode=json_mode,
            )
            text = result.get("text", "") if isinstance(result, dict) else ""
            if not text.strip():
                logger.warning(
                    "[EVAL_GEMINI] duty_name=%s reached_cap=true request_budget=%s requests_used=%s reason=empty_response",
                    budget.duty_name,
                    budget.request_budget,
                    requests_used,
                )
            return text
        except Exception as exc:
            logger.warning(
                "[EVAL_GEMINI] duty_name=%s reached_cap=true request_budget=%s requests_used=%s reason=%s",
                budget.duty_name,
                budget.request_budget,
                requests_used,
                exc,
            )
            return ""
