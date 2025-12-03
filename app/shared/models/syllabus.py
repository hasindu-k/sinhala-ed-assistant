# app/shared/models/syllabus.py

from sqlalchemy import Column, Integer, String, JSON
from app.core.database import Base

class Syllabus(Base):
    __tablename__ = "resource_syllabus"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, unique=True)
    syllabus_chunks = Column(JSON)  # list[str]
