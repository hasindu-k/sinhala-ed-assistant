# app/schemas/rubric.py

from pydantic import BaseModel, Field, validator
from typing import Optional
from uuid import UUID
from datetime import datetime


# Rubric Criterion Schemas
class RubricCriterionCreate(BaseModel):
    criterion: str = Field(..., description="Criterion name (semantic, coverage, relevance)")
    weight_percentage: float = Field(..., ge=0.0, le=1.0, description="Weight as decimal (e.g., 0.6 for 60%)")


class RubricCriterionUpdate(BaseModel):
    criterion: Optional[str] = None
    weight_percentage: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class RubricCriterionResponse(BaseModel):
    id: UUID
    rubric_id: UUID
    criterion: str
    weight_percentage: float
    created_at: datetime

    class Config:
        from_attributes = True


# Rubric Schemas
class RubricCreate(BaseModel):
    name: str = Field(..., description="Rubric name")
    description: Optional[str] = None
    rubric_type: str = Field(default="evaluation", description="Type of rubric")
    criteria: list[RubricCriterionCreate] = Field(..., min_items=3, max_items=3, description="Exactly 3 criteria required")

    @validator('criteria')
    def validate_criteria(cls, v):
        if len(v) != 3:
            raise ValueError('Exactly 3 criteria must be provided')
        
        criterion_names = [c.criterion.lower() for c in v]
        required_criteria = ['semantic', 'coverage', 'relevance']
        
        if not all(name in criterion_names for name in required_criteria):
            raise ValueError('Criteria must include: semantic, coverage, relevance')
        
        # Check weights sum to 1.0
        total_weight = sum(c.weight_percentage for c in v)
        if abs(total_weight - 1.0) > 0.001:  # Allow small floating point tolerance
            raise ValueError('Criteria weights must sum to 1.0')
        
        return v


class RubricUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    rubric_type: Optional[str] = None


class RubricResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    rubric_type: str
    created_by: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RubricDetail(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    rubric_type: str
    created_by: Optional[UUID] = None
    created_at: datetime
    criteria: list[RubricCriterionResponse] = Field(..., min_items=3, max_items=3)

    class Config:
        from_attributes = True
