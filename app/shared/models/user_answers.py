from sqlalchemy import Column, Integer, String, JSON
from app.core.database import Base

class UserAnswers(Base):
    __tablename__ = "user_answers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, unique=True)
    answers = Column(JSON)   # dict: {"Q01_a": "...", "Q01_b": "..."}
