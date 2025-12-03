# app/shared/models/syllabus.py

from sqlalchemy import Column, Integer, String, JSON
from core.database import Base

class Syllabus(Base):
    __tablename__ = "teacher_syllabus"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(String, index=True, unique=True)
    syllabus_chunks = Column(JSON)  # list[str]
