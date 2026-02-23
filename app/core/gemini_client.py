# app/core/gemini_client.py
import logging
import time
import random
import threading
from google import genai
from app.core.config import settings

logger = logging.getLogger(__name__)

_client = genai.Client(api_key=settings.GOOGLE_API_KEY)
MODEL_NAME = "gemini-2.0-flash"

# Increased from 5 → 10 to support parallel per-question Gemini feedback calls
# REVERTED: Reduce 10 → 5 to prevent aggressive 429 Resource Exhausted errors
_ai_semaphore = threading.Semaphore(5)

class GeminiClient:
    @classmethod
    def get_client(cls):
        """Return shared Gemini client"""
        return _client

    @classmethod
    def generate_content(cls, prompt: str, max_retries: int = 10, safety_settings: list = None, json_mode: bool = False) -> dict:
        """
        Generate content from Gemini and return text + token usage.
        Includes rate limiting (semaphore) and retry logic (exponential backoff).
        Token counting is estimated locally (no extra API round-trip).
        """
        client = cls.get_client()

        from google.genai import types
        config = types.GenerateContentConfig(
            safety_settings=safety_settings,
            response_mime_type="application/json" if json_mode else "text/plain"
        )

        # Estimate prompt tokens locally — avoids one API round-trip per call
        prompt_tokens_estimate = max(len(prompt) // 4, 1)

        for attempt in range(max_retries + 1):
            try:
                with _ai_semaphore:
                    response = client.models.generate_content(
                        model=MODEL_NAME,
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
                is_rate_limit = "429" in error_msg or "rate limit" in error_msg or "high demand" in error_msg
                is_overloaded = "503" in error_msg or "overloaded" in error_msg or "deadline exceeded" in error_msg

                if (is_rate_limit or is_overloaded) and attempt < max_retries:
                    # Exponential backoff: base_wait * (attempt+1) + jitter
                    # capped to avoid huge wait times that frustrate users
                    base_wait = 3 if is_rate_limit else 2
                    wait_time = min(30, (base_wait * (attempt + 1)) + random.uniform(1, 5))
                    
                    logger.warning(
                        f"Gemini API {'rate limited' if is_rate_limit else 'overloaded'} (Attempt {attempt+1}/{max_retries+1}). "
                        f"Retrying in {wait_time:.2f}s (Capped at 30s)... Error: {e}"
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Gemini API final failure after {attempt+1} attempts: {e}")
                    raise e

        return {"text": "", "error": "Maximum retries exceeded"}
