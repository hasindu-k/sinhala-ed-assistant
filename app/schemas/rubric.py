# app/schemas/rubric.py

from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


# Rubric Criterion Schemas
class RubricCriterionCreate(BaseModel):
    criterion: Optional[str] = None
    weight_percentage: Optional[int] = Field(default=None, ge=0, le=100)


class RubricCriterionUpdate(BaseModel):
    criterion: Optional[str] = None
    weight_percentage: Optional[int] = Field(default=None, ge=0, le=100)


class RubricCriterionResponse(BaseModel):
    id: UUID
    rubric_id: UUID
    criterion: Optional[str] = None
    weight_percentage: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Rubric Schemas
class RubricCreate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    rubric_type: Optional[str] = None
    criteria: list[RubricCriterionCreate] = []


class RubricUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    rubric_type: Optional[str] = None


class RubricResponse(BaseModel):
    id: UUID
    name: Optional[str] = None
    description: Optional[str] = None
    rubric_type: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RubricDetail(BaseModel):
    id: UUID
    name: Optional[str] = None
    description: Optional[str] = None
    rubric_type: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    criteria: list[RubricCriterionResponse] = []

    class Config:
        from_attributes = True
