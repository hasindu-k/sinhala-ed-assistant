# app/shared/ai/gemini_client.py

from app.core.gemini_client import GeminiClient
from google.genai import types 

MODEL_NAME = "gemini-3-flash-preview"

# Shared safety settings
SAFETY_SETTINGS = [
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
]

def gemini_generate(
    prompt: str,
    *,
    json_mode: bool = False,
) -> str:
    if not prompt or not prompt.strip():
        return ""

    client = GeminiClient.get_client()

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                safety_settings=SAFETY_SETTINGS,
                response_mime_type="application/json" if json_mode else "text/plain"
            ),
        )

        return response.text or ""

    except Exception as e:
        print(f"❌ Error during Gemini generation: {e}")
        return ""