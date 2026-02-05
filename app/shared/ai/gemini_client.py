# app/shared/ai/gemini_client.py

from app.core.gemini_client import GeminiClient
from google.genai.types import SafetySetting, HarmCategory, HarmBlockThreshold

MODEL_NAME = "gemini-3-flash-preview"

# Shared safety settings (safe for education use)
SAFETY_SETTINGS = [
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=HarmBlockThreshold.BLOCK_NONE,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=HarmBlockThreshold.BLOCK_NONE,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=HarmBlockThreshold.BLOCK_NONE,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=HarmBlockThreshold.BLOCK_NONE,
    ),
]


def gemini_generate(
    prompt: str,
    *,
    json_mode: bool = False,
) -> str:
    """
    Safe Gemini text generation wrapper.

    Args:
        prompt: Prompt text
        json_mode: If True, enforces JSON output

    Returns:
        Generated text (or JSON string)
    """
    if not prompt or not prompt.strip():
        return ""

    client = GeminiClient.get_client()

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            generation_config=(
                {"response_mime_type": "application/json"}
                if json_mode
                else None
            ),
            safety_settings=SAFETY_SETTINGS,
        )

        return response.text or ""

    except Exception as e:
        return ""
