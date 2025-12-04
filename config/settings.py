# config/settings.py

import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()  # loads .env file

class Settings:
    PROJECT_NAME: str = "Sinhala Educational Assistant"
    ENV: str = os.getenv("ENV", "development")

    # Gemini
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")

    # DB (future)
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")


settings = Settings()
