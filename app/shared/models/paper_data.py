from sqlalchemy import Column, Integer, String, JSON
from app.core.database import Base

class PaperData(Base):
    __tablename__ = "user_paper_data"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, unique=True)

    cleaned_text = Column(String)          # Full normalized OCR text
    structured_questions = Column(JSON)    # {"Q01_a": "...", "Q01_b": "..."}
