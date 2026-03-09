# app/shared/ai/gemini_client.py

from app.core.gemini_client import GeminiClient
from google.genai import types 
from google import genai
from app.core.config import settings
import logging
import time

logger = logging.getLogger(__name__)

MODEL_NAME = "gemini-2.5-flash-lite"
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
    model_name: str = None,
) -> str:
    if not prompt or not prompt.strip():
        return ""

    client = GeminiClient.get_client()
    
    selected_model = model_name or MODEL_NAME

    try:
        response = client.models.generate_content(
            model=selected_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                safety_settings=SAFETY_SETTINGS,
                response_mime_type="application/json" if json_mode else "text/plain"
            ),
        )
        print(f"DEBUG: gemini_generate called (fixed version). JSON Mode: {json_mode}, Model: {selected_model}")
        return response.text or ""

    except Exception as e:
        print(f"❌ Error during Gemini generation (model: {selected_model}): {e}")
        return ""

def gemini_generate_lightweight(content: str, prompt_template: str = None) -> str:
    """
    Use lightweight Gemini model for fast, simple tasks with minimal rate impact.
    Perfect for title generation, quick classifications, etc.
    Handles concurrent request rate limiting automatically.
    """
    if not content or not content.strip():
        return ""
    
    if prompt_template is None:
        prompt_template = """Act as an educational content classifier.
Task: Create a 4-word title for the content provided below.

Rules:
- Exactly 4 words.
- Use the same language as the input (English or Sinhala).
- No quotes, no periods, no introductory text.

Examples:
Input: "How do I solve quadratic equations using the formula?"
Title: Math Equations Help Guide
Input: "ශ්‍රී ලංකාවේ රජවරුන් ගැන තොරතුරු"
Title: ඉතිහාසය ශ්‍රී ලංකාව රජවරු

Input: {content}
Title:"""
    
    prompt = prompt_template.format(content=content)
    
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            api_key = getattr(settings, 'GEMINI_LIGHT_API_KEY', None)
            client = genai.Client(api_key=api_key)
            
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",  # Latest lite model
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="text/plain",
                    safety_settings=[
                        types.SafetySetting(
                            category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                            threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                        ),
                        types.SafetySetting(
                            category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                            threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                        ),
                    ]
                )
            )
            
            return (response.text or "").strip()
            
        except Exception as e:
            error_msg = str(e).lower()
            is_rate_limit = "429" in error_msg or "resource_exhausted" in error_msg
            
            if is_rate_limit and attempt < max_retries - 1:
                # Wait 1 second for rate limiting, then retry
                logger.debug(f"Rate limited on lightweight request (attempt {attempt + 1}), waiting 1s...")
                time.sleep(1)
                continue
            else:
                logger.warning(f"Lightweight Gemini generation failed: {e}")
                return ""
    
    return ""