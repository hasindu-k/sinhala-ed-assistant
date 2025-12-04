# app/core/config.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "SinLearn Evaluation Backend"

    DATABASE_URL: str
    GEMINI_API_KEY: str
    MODEL_EMBEDDING_NAME: str = "sentence-transformers/paraphrase-xlm-r-multilingual-v1"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
