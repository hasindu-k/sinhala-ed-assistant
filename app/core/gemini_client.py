import os
import google.generativeai as genai

class GeminiClient:
    _model = None

    @classmethod
    def load(cls):
        if cls._model is None:
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            cls._model = genai.GenerativeModel("gemini-2.5-flash")
        return cls._model
