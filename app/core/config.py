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

    # Auth
    JWT_SECRET_KEY: str = "change-me"  # override in .env
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 hours for development
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 15

    # Embedding model for RAG
    MODEL_EMBEDDING_NAME: str = "sentence-transformers/paraphrase-xlm-r-multilingual-v1"

    # Email (SMTP)
    MAIL_MAILER: str = "smtp"
    MAIL_HOST: str = "smtp.gmail.com"
    MAIL_PORT: int = 587
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    MAIL_ENCRYPTION: str = "tls"
    MAIL_FROM_ADDRESS: str = "admin@sinhalalearn.online"
    MAIL_FROM_NAME: str = "Sinhala Educational Assistant"
    FRONTEND_URL: str = "http://localhost:3000"  # for reset link

    BASE_FILE_STORAGE_PATH: str = "http://localhost:8000/"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"   # <- IMPORTANT: prevents "extra inputs forbidden" errors


settings = Settings()
