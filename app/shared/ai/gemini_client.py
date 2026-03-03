# app/shared/ai/gemini_client.py

from app.core.gemini_client import GeminiClient

MODEL_NAME = "gemini-2.0-flash"

def gemini_generate(
    prompt: str,
    *,
    json_mode: bool = False,
) -> str:
    if not prompt or not prompt.strip():
        return ""

    try:
        # Use the centralized GeminiClient which has retry logic and semaphores
        response = GeminiClient.generate_content(
            prompt=prompt,
            json_mode=json_mode
        )
        return response.get("text", "")

    except Exception as e:
        print(f"❌ Error during Gemini generation: {e}")
        return ""