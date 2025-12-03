# app/shared/models/paper_settings.py

from sqlalchemy import Column, Integer, String
from app.core.database import Base

class PaperSettings(Base):
    __tablename__ = "teacher_paper_settings"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(String, index=True, unique=True)

    total_marks = Column(Integer)                     # Entire paper marks
    total_main_questions = Column(Integer)           # e.g. 5
    required_main_questions = Column(Integer)        # e.g. 3
    subquestions_per_main = Column(Integer)          # e.g. 4
