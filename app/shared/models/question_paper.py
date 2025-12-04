from sqlalchemy import Column, Integer, String, Text, JSON
from app.core.database import Base

class UserQuestionPaper(Base):
    __tablename__ = "user_question_paper"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)

    raw_text = Column(Text)                 # original OCR text
    cleaned_text = Column(Text)             # normalized text
    structured_questions = Column(JSON)     # {"Q01_a": "...", ...}

    total_main_questions = Column(Integer)
    sub_questions_per_main = Column(Integer)
