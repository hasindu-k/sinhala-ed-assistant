import google.generativeai as genai
from config.settings import settings

class GeminiClient:
    _model = None

    @classmethod
    def load(cls):
        if cls._model is None:
            print("DEBUG: GOOGLE_API_KEY =", settings.GOOGLE_API_KEY)

            genai.configure(api_key=settings.GOOGLE_API_KEY)

            cls._model = genai.GenerativeModel("gemini-2.5-flash")

        return cls._model
