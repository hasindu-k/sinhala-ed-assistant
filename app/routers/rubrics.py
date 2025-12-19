from fastapi import APIRouter
from uuid import UUID
from app.schemas.rubric import RubricCreate

router = APIRouter()


@router.get("/")
def list_rubrics():
    """
    List system and user-created rubrics.
    """
    pass


@router.post("/")
def create_rubric(payload: RubricCreate):
    """
    Create a custom rubric.
    """
    pass


@router.get("/{rubric_id}")
def get_rubric(rubric_id: UUID):
    """
    Get rubric with criteria.
    """
    pass
