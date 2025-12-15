# app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to False in production, True for debugging
    poolclass=NullPool,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine
)

Base = declarative_base()

# Import all models here so they are registered with Base
from app.shared.models.user_chat import UserChat
from app.shared.models.resource_data import ResourceData
from app.shared.models.chat_messages import ChatMessage
from app.shared.models.text_chunk import TextChunk

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()