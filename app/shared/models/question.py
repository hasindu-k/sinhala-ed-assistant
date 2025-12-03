# app/shared/models/question.py

from sqlalchemy import Column, Integer, String, JSON
from app.core.database import Base

class Question(Base):
    __tablename__ = "user_questions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, unique=True)
    questions = Column(JSON)   # dict: {"Q01_a":"...", "Q01_b":"..."}
