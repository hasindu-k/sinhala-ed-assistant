# app/shared/models/rubric.py

from sqlalchemy import Column, Integer, String, Float
from app.core.database import Base

class Rubric(Base):
    __tablename__ = "user_rubric"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, unique=True)

    semantic_weight = Column(Float)
    coverage_weight = Column(Float)
    bm25_weight = Column(Float)
