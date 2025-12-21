# app/repositories/evaluation/rubric_repository.py

from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.shared.models.rubrics import Rubric, RubricCriterion


class RubricRepository:
    """Data access layer for Rubric and RubricCriterion models."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_rubric(
        self,
        created_by: Optional[UUID],
        name: str,
        description: Optional[str] = None,
        rubric_type: Optional[str] = None,
    ) -> Rubric:
        """Create a new rubric."""
        rubric = Rubric(
            created_by=created_by,
            name=name,
            description=description,
            rubric_type=rubric_type,
        )
        self.db.add(rubric)
        self.db.commit()
        self.db.refresh(rubric)
        return rubric
    
    def get_rubric(self, rubric_id: UUID) -> Optional[Rubric]:
        """Get rubric by ID."""
        return self.db.query(Rubric).filter(Rubric.id == rubric_id).first()
    
    def get_rubrics_by_user(self, user_id: UUID) -> List[Rubric]:
        """Get all rubrics for a user (created_by)."""
        # Backward-compatible method name; the underlying column is created_by
        return self.db.query(Rubric).filter(Rubric.created_by == user_id).all()

    def get_rubrics_by_creator(self, created_by: UUID) -> List[Rubric]:
        """Get all rubrics created by a specific user."""
        return self.db.query(Rubric).filter(Rubric.created_by == created_by).all()

    def get_system_rubrics(self) -> List[Rubric]:
        """Get all system rubrics (created_by is NULL or rubric_type == 'system')."""
        return self.db.query(Rubric).filter(
            (Rubric.created_by == None) | (Rubric.rubric_type == 'system')
        ).all()
    
    def update_rubric(
        self,
        rubric_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        rubric_type: Optional[str] = None,
    ) -> Optional[Rubric]:
        """Update rubric."""
        rubric = self.get_rubric(rubric_id)
        if rubric:
            if name is not None:
                rubric.name = name
            if description is not None:
                rubric.description = description
            if rubric_type is not None:
                rubric.rubric_type = rubric_type
            self.db.commit()
            self.db.refresh(rubric)
        return rubric
    
    def delete_rubric(self, rubric_id: UUID) -> bool:
        """Delete rubric and its criteria."""
        rubric = self.get_rubric(rubric_id)
        if rubric:
            self.db.delete(rubric)
            self.db.commit()
            return True
        return False
    
    def create_rubric_criterion(
        self,
        rubric_id: UUID,
        criterion: Optional[str] = None,
        weight_percentage: Optional[int] = None,
    ) -> RubricCriterion:
        """Create a rubric criterion."""
        criterion_obj = RubricCriterion(
            rubric_id=rubric_id,
            criterion=criterion,
            weight_percentage=weight_percentage,
        )
        self.db.add(criterion_obj)
        self.db.commit()
        self.db.refresh(criterion_obj)
        return criterion_obj
    
    def get_rubric_criteria(self, rubric_id: UUID) -> List[RubricCriterion]:
        """Get all criteria for a rubric."""
        return self.db.query(RubricCriterion).filter(
            RubricCriterion.rubric_id == rubric_id
        ).all()

    def update_rubric_criterion(
        self,
        rubric_id: UUID,
        criterion_id: UUID,
        criterion: Optional[str] = None,
        weight_percentage: Optional[int] = None,
    ) -> Optional[RubricCriterion]:
        """Update a rubric criterion scoped by rubric id."""
        criterion_obj = self.db.query(RubricCriterion).filter(
            RubricCriterion.id == criterion_id,
            RubricCriterion.rubric_id == rubric_id,
        ).first()
        if criterion_obj:
            if criterion is not None:
                criterion_obj.criterion = criterion
            if weight_percentage is not None:
                criterion_obj.weight_percentage = weight_percentage
            self.db.commit()
            self.db.refresh(criterion_obj)
        return criterion_obj

    def delete_rubric_criterion(self, rubric_id: UUID, criterion_id: UUID) -> bool:
        """Delete a rubric criterion scoped by rubric id."""
        criterion = self.db.query(RubricCriterion).filter(
            RubricCriterion.id == criterion_id,
            RubricCriterion.rubric_id == rubric_id,
        ).first()
        if criterion:
            self.db.delete(criterion)
            self.db.commit()
            return True
        return False
    
    def get_rubric_with_criteria(self, rubric_id: UUID) -> Optional[dict]:
        """Get rubric with all its criteria."""
        rubric = self.get_rubric(rubric_id)
        if not rubric:
            return None
        
        criteria = self.get_rubric_criteria(rubric_id)
        
        return {
            "id": rubric.id,
            "created_by": rubric.created_by,
            "name": rubric.name,
            "description": rubric.description,
            "rubric_type": rubric.rubric_type,
            "created_at": rubric.created_at,
            "criteria": [
                {
                    "id": c.id,
                    "rubric_id": c.rubric_id,
                    "criterion": c.criterion,
                    "weight_percentage": c.weight_percentage,
                    "created_at": c.created_at,
                }
                for c in criteria
            ]
        }
