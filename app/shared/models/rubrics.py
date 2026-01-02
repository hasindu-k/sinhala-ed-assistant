# app/shared/models/rubrics.py

import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class Rubric(Base):
    __tablename__ = "rubrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    rubric_type = Column(String, nullable=True) # system or custom
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True) # null for system rubrics
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RubricCriterion(Base):
    __tablename__ = "rubric_criteria"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rubric_id = Column(UUID(as_uuid=True), ForeignKey("rubrics.id"), nullable=False, index=True)
    criterion = Column(String, nullable=True) # semantic | coverage | relevance
    weight_percentage = Column(Float, nullable=True)  # Changed to Float for decimal weights
    created_at = Column(DateTime(timezone=True), server_default=func.now())
