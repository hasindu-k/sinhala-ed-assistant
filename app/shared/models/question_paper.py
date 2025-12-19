from sqlalchemy import Column, Integer, String, Text, JSON
from app.core.database import Base


class UserQuestionPaper(Base):
    __tablename__ = "user_question_paper"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)

    raw_text = Column(Text)                 # optional legacy
    cleaned_text = Column(Text)             # optional legacy
    structured_questions = Column(JSON)     # optional legacy support

    paper_structure = Column(JSON)          # authoritative

    total_main_questions = Column(Integer)
