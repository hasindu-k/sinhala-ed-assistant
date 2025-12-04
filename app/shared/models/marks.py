# app/shared/models/marks.py

from sqlalchemy import Column, Integer, String, JSON
from app.core.database import Base

class Marks(Base):
    __tablename__ = "evaluated_marks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)

    # Dictionary:
    # { "Q01": [3,3,6,8], "Q02": [3,3,6,8], ... }
    marks_distribution = Column(JSON)
