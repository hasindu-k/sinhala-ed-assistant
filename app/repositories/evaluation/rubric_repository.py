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
        user_id: UUID,
        name: str,
        description: Optional[str] = None
    ) -> Rubric:
        """Create a new rubric."""
        rubric = Rubric(
            user_id=user_id,
            name=name,
            description=description
        )
        self.db.add(rubric)
        self.db.commit()
        self.db.refresh(rubric)
        return rubric
    
    def get_rubric(self, rubric_id: UUID) -> Optional[Rubric]:
        """Get rubric by ID."""
        return self.db.query(Rubric).filter(Rubric.id == rubric_id).first()
    
    def get_rubrics_by_user(self, user_id: UUID) -> List[Rubric]:
        """Get all rubrics for a user."""
        return self.db.query(Rubric).filter(Rubric.user_id == user_id).all()
    
    def update_rubric(
        self,
        rubric_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[Rubric]:
        """Update rubric."""
        rubric = self.get_rubric(rubric_id)
        if rubric:
            if name is not None:
                rubric.name = name
            if description is not None:
                rubric.description = description
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
        criterion_name: str,
        description: Optional[str] = None,
        weight: int = 0
    ) -> RubricCriterion:
        """Create a rubric criterion."""
        criterion = RubricCriterion(
            rubric_id=rubric_id,
            criterion_name=criterion_name,
            description=description,
            weight=weight
        )
        self.db.add(criterion)
        self.db.commit()
        self.db.refresh(criterion)
        return criterion
    
    def get_rubric_criteria(self, rubric_id: UUID) -> List[RubricCriterion]:
        """Get all criteria for a rubric."""
        return self.db.query(RubricCriterion).filter(
            RubricCriterion.rubric_id == rubric_id
        ).all()
    
    def get_rubric_with_criteria(self, rubric_id: UUID) -> Optional[dict]:
        """Get rubric with all its criteria."""
        rubric = self.get_rubric(rubric_id)
        if not rubric:
            return None
        
        criteria = self.get_rubric_criteria(rubric_id)
        
        return {
            "id": rubric.id,
            "user_id": rubric.user_id,
            "name": rubric.name,
            "description": rubric.description,
            "created_at": rubric.created_at,
            "criteria": [
                {
                    "id": c.id,
                    "criterion_name": c.criterion_name,
                    "description": c.description,
                    "weight": c.weight
                }
                for c in criteria
            ]
        }
