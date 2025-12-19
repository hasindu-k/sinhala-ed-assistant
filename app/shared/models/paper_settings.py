from sqlalchemy import Column, Integer, String
from app.core.database import Base


class PaperSettings(Base):
    __tablename__ = "user_paper_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, unique=True)

    total_marks = Column(Integer)
    total_main_questions = Column(Integer)
    required_main_questions = Column(Integer)
