#app/core/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # General app info
    APP_NAME: str = "Sinhala Educational Assistant"
    ENV: str = "development"

    # Gemini
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None

    # Database (optional)
    DATABASE_URL: Optional[str] = None

    # Embedding model for RAG
    MODEL_EMBEDDING_NAME: str = "sentence-transformers/paraphrase-xlm-r-multilingual-v1"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"   # <- IMPORTANT: prevents "extra inputs forbidden" errors


settings = Settings()
