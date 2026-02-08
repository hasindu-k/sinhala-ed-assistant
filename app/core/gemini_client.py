# app/core/gemini_client.py

from google import genai
from app.core.config import settings

_client = genai.Client(api_key=settings.GOOGLE_API_KEY)
MODEL_NAME = "gemini-3-flash-preview"

class GeminiClient:
    @classmethod
    def get_client(cls):
        """Return shared Gemini client"""
        return _client

    @classmethod
    def generate_content(cls, prompt: str) -> dict:
        """
        Generate content from Gemini and return text + token usage
        """
        client = cls.get_client()

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

        # ✅ Completion token estimation (SDK does not expose exact value yet)
        completion_tokens = max(len(text) // 4, 1)

        total_tokens = prompt_tokens + completion_tokens

        return {
            "text": text,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        }
