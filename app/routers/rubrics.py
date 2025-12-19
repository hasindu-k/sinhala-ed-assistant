from fastapi import APIRouter
from uuid import UUID
from app.schemas.rubric import (
    RubricCreate,
    RubricUpdate,
    RubricResponse,
    RubricDetail,
    RubricCriterionCreate,
    RubricCriterionUpdate,
    RubricCriterionResponse
)
from typing import List

router = APIRouter()


@router.get("/", response_model=List[RubricResponse])
def list_rubrics():
    """
    List system and user-created rubrics.
    """
    pass


@router.post("/", response_model=RubricResponse)
def create_rubric(payload: RubricCreate):
    """
    Create a custom rubric.
    """
    pass


@router.get("/{rubric_id}", response_model=RubricDetail)
def get_rubric(rubric_id: UUID):
    """
    Get rubric with criteria.
    """
    pass


@router.put("/{rubric_id}", response_model=RubricResponse)
def update_rubric(rubric_id: UUID, payload: RubricUpdate):
    """
    Update rubric metadata.
    """
    pass


@router.delete("/{rubric_id}")
def delete_rubric(rubric_id: UUID):
    """
    Delete a rubric.
    """
    pass


@router.post("/{rubric_id}/criteria", response_model=RubricCriterionResponse)
def add_criterion(rubric_id: UUID, payload: RubricCriterionCreate):
    """
    Add a criterion to a rubric.
    """
    pass


@router.put("/{rubric_id}/criteria/{criterion_id}", response_model=RubricCriterionResponse)
def update_criterion(rubric_id: UUID, criterion_id: UUID, payload: RubricCriterionUpdate):
    """
    Update a rubric criterion.
    """
    pass


@router.delete("/{rubric_id}/criteria/{criterion_id}")
def delete_criterion(rubric_id: UUID, criterion_id: UUID):
    """
    Delete a rubric criterion.
    """
    pass
