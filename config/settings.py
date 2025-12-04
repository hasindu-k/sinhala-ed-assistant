# config/settings.py

import os
from dotenv import load_dotenv

load_dotenv()  # loads .env file

class Settings:
    PROJECT_NAME: str = "Sinhala Educational Assistant"
    ENV: str = os.getenv("ENV", "development")

    # Gemini / Google AI
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")

    # DB (if you add later)
    DATABASE_URL: str | None = os.getenv("DATABASE_URL")


settings = Settings()

# You can import with:
# from config.settings import settings
