# app/core/gemini_client.py
import google.generativeai as genai
from app.core.config import settings


class GeminiClient:
    _model = None

    @classmethod
    def load(cls):
        if cls._model is None:
            print("DEBUG: GOOGLE_API_KEY =", settings.GOOGLE_API_KEY)

            genai.configure(api_key=settings.GOOGLE_API_KEY)

            cls._model = genai.GenerativeModel("gemini-3-flash-preview")

        return cls._model
    
    @classmethod
    def generate_content(cls, prompt: str) -> dict:
        """
        Generate content from Gemini
        """
        model = cls.load()
        # Count tokens using the model's count_tokens method
        token_count_response = model.count_tokens(prompt)
        prompt_tokens = token_count_response.total_tokens
        response = model.generate_content(prompt)

        if hasattr(response, "usage_metadata") and hasattr(response.usage_metadata, "candidates_token_count"):
            completion_tokens = response.usage_metadata.candidates_token_count
        else:
            # fallback to rough estimate
            completion_tokens = len(response.text) // 4

        total_tokens = prompt_tokens + completion_tokens

        return {
            "text": response.text,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        }