# app/shared/ai/gemini_client.py

import google.generativeai as genai
from app.core.config import settings


# ------------------------------------------------------------
# 1. Configure Gemini at startup
# ------------------------------------------------------------
genai.configure(api_key=settings.GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-3-flash-preview")


# ------------------------------------------------------------
# 2. Safe wrapper for text generation
# ------------------------------------------------------------
def gemini_generate(prompt: str) -> str:
    try:
        response = model.generate_content(prompt)
        if hasattr(response, "text"):
            return response.text
        return str(response)
    except Exception as e:
        return f"Feedback generation failed due to an internal error."
