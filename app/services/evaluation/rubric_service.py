# app/services/evaluation/rubric_service.py

from typing import Optional, List, Dict
from uuid import UUID
from sqlalchemy.orm import Session

from app.shared.models.rubrics import Rubric, RubricCriterion


def create_rubric(
    *,
    db: Session,
    name: str,
    description: Optional[str] = None,
    rubric_type: Optional[str] = None,
    created_by: Optional[UUID] = None
) -> Rubric:
    """Create a new rubric."""
    rubric = Rubric(
        name=name,
        description=description,
        rubric_type=rubric_type,
        created_by=created_by
    )
    db.add(rubric)
    db.commit()
    db.refresh(rubric)
    return rubric


def get_rubric(
    *,
    db: Session,
    rubric_id: UUID
) -> Optional[Rubric]:
    """Get rubric by ID."""
    return db.query(Rubric).filter(Rubric.id == rubric_id).first()


def get_rubrics_by_user(
    *,
    db: Session,
    user_id: UUID
) -> List[Rubric]:
    """Get all rubrics created by a user."""
    return db.query(Rubric).filter(Rubric.created_by == user_id).all()


def update_rubric(
    *,
    db: Session,
    rubric_id: UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
    rubric_type: Optional[str] = None
) -> Optional[Rubric]:
    """Update rubric details."""
    rubric = get_rubric(db=db, rubric_id=rubric_id)
    if rubric:
        if name is not None:
            rubric.name = name
        if description is not None:
            rubric.description = description
        if rubric_type is not None:
            rubric.rubric_type = rubric_type
        db.commit()
        db.refresh(rubric)
    return rubric


def delete_rubric(
    *,
    db: Session,
    rubric_id: UUID
) -> bool:
    """Delete a rubric and its criteria."""
    rubric = get_rubric(db=db, rubric_id=rubric_id)
    if rubric:
        db.query(RubricCriterion).filter(RubricCriterion.rubric_id == rubric_id).delete()
        db.delete(rubric)
        db.commit()
        return True
    return False


def create_rubric_criterion(
    *,
    db: Session,
    rubric_id: UUID,
    criterion: str,
    weight_percentage: int
) -> RubricCriterion:
    """Add a criterion to a rubric."""
    criterion_obj = RubricCriterion(
        rubric_id=rubric_id,
        criterion=criterion,
        weight_percentage=weight_percentage
    )
    db.add(criterion_obj)
    db.commit()
    db.refresh(criterion_obj)
    return criterion_obj


def get_rubric_criteria(
    *,
    db: Session,
    rubric_id: UUID
) -> List[RubricCriterion]:
    """Get all criteria for a rubric."""
    return db.query(RubricCriterion).filter(
        RubricCriterion.rubric_id == rubric_id
    ).all()


def create_rubric_with_criteria(
    *,
    db: Session,
    name: str,
    criteria: List[Dict],
    description: Optional[str] = None,
    rubric_type: Optional[str] = None,
    created_by: Optional[UUID] = None
) -> Rubric:
    """
    Create a rubric with criteria in one transaction.
    
    criteria format:
    [
        {"criterion": "Semantic Similarity", "weight_percentage": 40},
        {"criterion": "Coverage", "weight_percentage": 30},
        {"criterion": "BM25 Score", "weight_percentage": 30}
    ]
    """
    total_weight = sum(c["weight_percentage"] for c in criteria)
    if total_weight != 100:
        raise ValueError(f"Criteria weights must sum to 100, got {total_weight}")
    
    rubric = create_rubric(
        db=db,
        name=name,
        description=description,
        rubric_type=rubric_type,
        created_by=created_by
    )
    
    for criterion_data in criteria:
        create_rubric_criterion(
            db=db,
            rubric_id=rubric.id,
            criterion=criterion_data["criterion"],
            weight_percentage=criterion_data["weight_percentage"]
        )
    
    return rubric


def get_rubric_with_criteria(
    *,
    db: Session,
    rubric_id: UUID
) -> Optional[Dict]:
    """Get complete rubric with all criteria."""
    rubric = get_rubric(db=db, rubric_id=rubric_id)
    if not rubric:
        return None
    
    criteria = get_rubric_criteria(db=db, rubric_id=rubric_id)
    
    return {
        "id": rubric.id,
        "name": rubric.name,
        "description": rubric.description,
        "rubric_type": rubric.rubric_type,
        "created_by": rubric.created_by,
        "created_at": rubric.created_at,
        "criteria": [
            {
                "id": c.id,
                "criterion": c.criterion,
                "weight_percentage": c.weight_percentage,
                "created_at": c.created_at
            }
            for c in criteria
        ]
    }


def create_evaluation_rubric(
    *,
    db: Session,
    semantic_weight: float,
    coverage_weight: float,
    bm25_weight: float,
    created_by: Optional[UUID] = None
) -> Rubric:
    """
    Create a standard evaluation rubric with semantic, coverage, and BM25 criteria.
    Weights should be between 0 and 1 and sum to 1.
    """
    total = semantic_weight + coverage_weight + bm25_weight
    if abs(total - 1.0) > 0.01:
        raise ValueError(f"Weights must sum to 1.0, got {total}")
    
    criteria = [
        {"criterion": "Semantic Similarity", "weight_percentage": int(semantic_weight * 100)},
        {"criterion": "Coverage", "weight_percentage": int(coverage_weight * 100)},
        {"criterion": "BM25 Score", "weight_percentage": int(bm25_weight * 100)}
    ]
    
    return create_rubric_with_criteria(
        db=db,
        name="Evaluation Rubric",
        criteria=criteria,
        rubric_type="evaluation",
        created_by=created_by
    )