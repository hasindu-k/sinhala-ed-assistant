import os
import logging
import time
import random
import threading
from google import genai
from app.core.config import settings

logger = logging.getLogger(__name__)

_client = genai.Client(api_key=settings.GOOGLE_API_KEY)
MODEL_NAME = "gemini-3-flash-preview"

# Global semaphore to limit concurrent AI calls across all threads
# This prevents overloading the API and hitting "high demand" errors
_ai_semaphore = threading.Semaphore(5)

class GeminiClient:
    @classmethod
    def get_client(cls):
        """Return shared Gemini client"""
        return _client

    @classmethod
    def generate_content(cls, prompt: str, max_retries: int = 3) -> dict:
        """
        Generate content from Gemini and return text + token usage.
        Includes rate limiting (semaphore) and retry logic (exponential backoff).
        """
        client = cls.get_client()
        
        for attempt in range(max_retries + 1):
            try:
                with _ai_semaphore:
                    # ✅ Count prompt tokens
                    token_resp = client.models.count_tokens(
                        model=MODEL_NAME,
                        contents=prompt
                    )
                    prompt_tokens = token_resp.total_tokens

                    # ✅ Generate content
                    response = client.models.generate_content(
                        model=MODEL_NAME,
                        contents=prompt
                    )

                    text = response.text or ""

                    # ✅ Completion token estimation
                    completion_tokens = max(len(text) // 4, 1)
                    total_tokens = prompt_tokens + completion_tokens

                    return {
                        "text": text,
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens
                    }

            except Exception as e:
                error_msg = str(e).lower()
                is_rate_limit = "429" in error_msg or "rate limit" in error_msg or "high demand" in error_msg
                is_overloaded = "503" in error_msg or "overloaded" in error_msg or "deadline exceeded" in error_msg
                
                if (is_rate_limit or is_overloaded) and attempt < max_retries:
                    # Exponential backoff: 2^attempt + jitter
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Gemini API rate limited/overloaded (Attempt {attempt+1}/{max_retries+1}). Retrying in {wait_time:.2f}s... Error: {e}")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Gemini API final failure after {attempt+1} attempts: {e}")
                    raise e

        # Fallback (should not be reached due to raise)
        return {"text": "", "error": "Maximum retries exceeded"}
