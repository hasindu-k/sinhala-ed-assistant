# app/core/gemini_client.py
import logging
import time
import random
import threading
from google import genai
from app.core.config import settings

logger = logging.getLogger(__name__)

def _collect_api_keys() -> list[str]:
    """Collect configured API keys in priority order without duplicates."""
    raw_keys = [
        settings.GOOGLE_API_KEY,
        getattr(settings, "GOOGLE_API_KEY_V2", None),
        settings.GEMINI_API_KEY,
    ]
    keys: list[str] = []
    for key in raw_keys:
        if key and key.strip() and key not in keys:
            keys.append(key.strip())
    return keys


_api_keys = _collect_api_keys()
_clients = [genai.Client(api_key=key) for key in _api_keys]
_active_client_index = 0
_client_index_lock = threading.Lock()

if _api_keys:
    logger.info("Initialized Gemini client(s) with %s API key(s).", len(_api_keys))
    logger.debug("Gemini primary key details: %s...", _api_keys[0][:10])
else:
    logger.warning("No Gemini API key found. Set GOOGLE_API_KEY and optionally GOOGLE_API_KEY_V2.")

MODEL_NAME = "gemini-2.5-flash"
MODEL_FALLBACKS = [
    MODEL_NAME,
    "gemini-2.5-pro",
    "gemini-1.5-flash",
]
_active_model_index = 0
_model_index_lock = threading.Lock()

# Increased from 5 → 10 to support parallel per-question Gemini feedback calls
# SAFER: Set to 5 to support faster parallel feedback generation while remaining within typical API limits
_ai_semaphore = threading.Semaphore(5)

class GeminiClient:
    @classmethod
    def get_client(cls):
        """Return shared Gemini client"""
        if not _clients:
            raise ValueError("No Gemini API key configured. Set GOOGLE_API_KEY (or GOOGLE_API_KEY_V2).")
        return _clients[_active_client_index]

    @classmethod
    def _switch_to_next_client(cls) -> bool:
        """Switch to next available key/client if configured."""
        global _active_client_index
        if len(_clients) < 2:
            return False

        with _client_index_lock:
            previous = _active_client_index
            _active_client_index = (_active_client_index + 1) % len(_clients)
            switched = _active_client_index != previous

        if switched:
            logger.warning(
                "Switched Gemini API key from slot %s to slot %s.",
                previous,
                _active_client_index,
            )
        return switched

    @classmethod
    def _get_model_name(cls) -> str:
        return MODEL_FALLBACKS[_active_model_index]

    @classmethod
    def _switch_to_next_model(cls) -> bool:
        global _active_model_index
        if len(MODEL_FALLBACKS) < 2:
            return False

        with _model_index_lock:
            previous = _active_model_index
            _active_model_index = (_active_model_index + 1) % len(MODEL_FALLBACKS)
            switched = _active_model_index != previous

        if switched:
            logger.warning(
                "Switched Gemini model from %s to %s.",
                MODEL_FALLBACKS[previous],
                MODEL_FALLBACKS[_active_model_index],
            )
        return switched

    @staticmethod
    def _classify_retry(error_msg: str) -> str | None:
        is_rate_limit = "429" in error_msg or "rate limit" in error_msg or "high demand" in error_msg
        if is_rate_limit:
            return "rate_limited"

        is_overloaded = "503" in error_msg or "overloaded" in error_msg or "deadline exceeded" in error_msg
        if is_overloaded:
            return "overloaded"

        is_auth_error = (
            "unauthenticated" in error_msg
            or "invalid api key" in error_msg
            or "api key not valid" in error_msg
            or "permission denied" in error_msg
        )
        if is_auth_error:
            return "auth_failed"

        is_model_missing = (
            "404" in error_msg
            and (
                "not_found" in error_msg
                or "no longer available" in error_msg
                or "model" in error_msg
            )
        )
        if is_model_missing:
            return "model_not_found"

        return None

    @staticmethod
    def _get_wait_time(reason: str, attempt: int) -> float:
        if reason == "model_not_found":
            return 0
        base_wait = 3 if reason == "rate_limited" else 2
        return min(30, (base_wait * (attempt + 1)) + random.uniform(1, 5))

    @classmethod
    def generate_content(cls, prompt: str, max_retries: int = 15, safety_settings: list = None, json_mode: bool = False) -> dict:
        """
        Generate content from Gemini and return text + token usage.
        Includes rate limiting (semaphore) and retry logic (exponential backoff).
        Token counting is estimated locally (no extra API round-trip).
        """
        from google.genai import types
        config = types.GenerateContentConfig(
            safety_settings=safety_settings,
            response_mime_type="application/json" if json_mode else "text/plain",
            max_output_tokens=8192
        )

        # Estimate prompt tokens locally — avoids one API round-trip per call
        prompt_tokens_estimate = max(len(prompt) // 4, 1)

        for attempt in range(max_retries + 1):
            try:
                client = cls.get_client()
                with _ai_semaphore:
                    response = client.models.generate_content(
                        model=cls._get_model_name(),
                        contents=prompt,
                        config=config
                    )

                    text = response.text or ""

                    # Completion token estimation
                    completion_tokens = max(len(text) // 4, 1)
                    total_tokens = prompt_tokens_estimate + completion_tokens

                    return {
                        "text": text,
                        "prompt_tokens": prompt_tokens_estimate,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens
                    }

            except Exception as e:
                error_msg = str(e).lower()
                retry_reason = cls._classify_retry(error_msg)

                if retry_reason and attempt < max_retries:
                    if retry_reason == "model_not_found":
                        cls._switch_to_next_model()
                    else:
                        # If multiple keys are configured, rotate keys before backing off.
                        cls._switch_to_next_client()

                    # Exponential backoff: base_wait * (attempt+1) + jitter
                    # capped to avoid huge wait times that frustrate users
                    wait_time = cls._get_wait_time(retry_reason, attempt)
                    
                    logger.warning(
                        f"Gemini API {retry_reason} (Attempt {attempt+1}/{max_retries+1}). "
                        f"Retrying in {wait_time:.2f}s (Capped at 30s)... Error: {e}"
                    )
                    if wait_time > 0:
                        time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Gemini API final failure after {attempt+1} attempts: {e}")
                    raise e

        return {"text": "", "error": "Maximum retries exceeded"}
