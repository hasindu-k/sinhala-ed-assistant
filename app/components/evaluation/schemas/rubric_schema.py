from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from uuid import UUID


class RubricCriterionCreate(BaseModel):
    criterion: str
    weight_percentage: int


class RubricCriterionResponse(BaseModel):
    id: UUID
    rubric_id: UUID
    criterion: str
    weight_percentage: int
    created_at: datetime

    class Config:
        from_attributes = True


class RubricCreate(BaseModel):
    name: str
    description: Optional[str] = None
    rubric_type: Optional[str] = None
    criteria: Optional[List[RubricCriterionCreate]] = []


class RubricUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    rubric_type: Optional[str] = None


class RubricResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    rubric_type: Optional[str]
    created_by: Optional[UUID]
    created_at: datetime
    criteria: Optional[List[RubricCriterionResponse]] = []

    class Config:
        from_attributes = True
