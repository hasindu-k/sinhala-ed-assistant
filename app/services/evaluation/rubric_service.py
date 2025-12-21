# app/services/evaluation/rubric_service.py

from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.evaluation.rubric_repository import RubricRepository
from app.schemas.rubric import RubricCriterionCreate


class RubricService:
    """Business logic for rubric management."""
    
    def __init__(self, db: Session):
        self.repository = RubricRepository(db)
        self.db = db

    def _get_owned_rubric(self, rubric_id: UUID, user_id: UUID):
        rubric = self.repository.get_rubric(rubric_id)
        if not rubric:
            raise ValueError("Rubric not found")
        # Ownership is required for write operations; system rubrics (created_by is None) are not writable
        if rubric.created_by != user_id:
            raise PermissionError("You don't have permission to modify this rubric")
        return rubric

    def _get_accessible_rubric(self, rubric_id: UUID, user_id: UUID):
        """Allow reading system rubrics (created_by is None) or owned rubrics."""
        rubric = self.repository.get_rubric(rubric_id)
        if not rubric:
            raise ValueError("Rubric not found")
        if rubric.created_by is not None and rubric.created_by != user_id:
            raise PermissionError("You don't have permission to access this rubric")
        return rubric

    def create_rubric(
        self,
        user_id: UUID,
        name: str,
        description: Optional[str] = None,
        rubric_type: Optional[str] = None,
        criteria: Optional[List[dict]] = None,
    ):
        """Create a new rubric; optionally add criteria."""
        rubric = self.repository.create_rubric(
            created_by=user_id,
            name=name,
            description=description,
            rubric_type=rubric_type,
        )
        if criteria:
            for criterion_data in criteria:
                self.repository.create_rubric_criterion(
                    rubric_id=rubric.id,
                    criterion=criterion_data.get("criterion"),
                    weight_percentage=criterion_data.get("weight_percentage"),
                )
        return rubric

    def create_system_rubric(
        self,
        name: str,
        description: Optional[str] = None,
        criteria: Optional[List[RubricCriterionCreate]] = None,
    ):
        """Create a system rubric (created_by=None, rubric_type='system')."""
        rubric = self.repository.create_rubric(
            created_by=None,
            name=name,
            description=description,
            rubric_type="system",
        )
        if criteria:
            for c in criteria:
                self.repository.create_rubric_criterion(
                    rubric_id=rubric.id,
                    criterion=c.criterion,
                    weight_percentage=c.weight_percentage,
                )
        return rubric
    
    def get_rubric(self, rubric_id: UUID):
        """Get rubric by ID."""
        return self.repository.get_rubric(rubric_id)

    def get_rubric_for_user(self, rubric_id: UUID, user_id: UUID):
        """Get rubric after ownership validation."""
        return self._get_owned_rubric(rubric_id, user_id)
    
    def get_rubrics_by_user(self, user_id: UUID) -> List:
        """Get system and user-created rubrics for a user."""
        user_rubrics = self.repository.get_rubrics_by_creator(user_id)
        system_rubrics = self.repository.get_system_rubrics()
        return user_rubrics + system_rubrics
    
    def update_rubric(
        self,
        rubric_id: UUID,
        user_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        rubric_type: Optional[str] = None,
    ):
        """Update rubric (owned by user)."""
        self._get_owned_rubric(rubric_id, user_id)
        return self.repository.update_rubric(
            rubric_id=rubric_id,
            name=name,
            description=description,
            rubric_type=rubric_type,
        )
    
    def delete_rubric(self, rubric_id: UUID, user_id: UUID) -> bool:
        """Delete rubric."""
        self._get_owned_rubric(rubric_id, user_id)
        return self.repository.delete_rubric(rubric_id)
    
    def create_rubric_criterion(
        self,
        rubric_id: UUID,
        user_id: UUID,
        criterion: Optional[str] = None,
        weight_percentage: Optional[int] = None,
    ):
        """Create a rubric criterion (owned rubric)."""
        self._get_owned_rubric(rubric_id, user_id)
        return self.repository.create_rubric_criterion(
            rubric_id=rubric_id,
            criterion=criterion,
            weight_percentage=weight_percentage,
        )
    
    def get_rubric_criteria(self, rubric_id: UUID, user_id: UUID) -> List:
        """Get all criteria for a rubric."""
        self._get_owned_rubric(rubric_id, user_id)
        return self.repository.get_rubric_criteria(rubric_id)

    def update_rubric_criterion(
        self,
        rubric_id: UUID,
        criterion_id: UUID,
        user_id: UUID,
        criterion: Optional[str] = None,
        weight_percentage: Optional[int] = None,
    ):
        """Update a rubric criterion after ownership validation."""
        self._get_owned_rubric(rubric_id, user_id)
        return self.repository.update_rubric_criterion(
            rubric_id=rubric_id,
            criterion_id=criterion_id,
            criterion=criterion,
            weight_percentage=weight_percentage,
        )

    def delete_rubric_criterion(self, rubric_id: UUID, criterion_id: UUID, user_id: UUID) -> bool:
        """Delete a rubric criterion after ownership validation."""
        self._get_owned_rubric(rubric_id, user_id)
        return self.repository.delete_rubric_criterion(rubric_id, criterion_id)
    
    def create_rubric_with_criteria(
        self,
        user_id: UUID,
        name: str,
        criteria: List[dict],
        description: Optional[str] = None,
        rubric_type: Optional[str] = None,
    ):
        """Create a complete rubric with criteria (criterion, weight_percentage)."""
        rubric = self.repository.create_rubric(
            created_by=user_id,
            name=name,
            description=description,
            rubric_type=rubric_type,
        )
        for criterion_data in criteria:
            self.repository.create_rubric_criterion(
                rubric_id=rubric.id,
                criterion=criterion_data.get("criterion"),
                weight_percentage=criterion_data.get("weight_percentage"),
            )
        return rubric
    
    def get_rubric_with_criteria(self, rubric_id: UUID, user_id: UUID) -> Optional[dict]:
        """Get rubric with all its criteria; allow access to system rubrics or owned rubrics."""
        self._get_accessible_rubric(rubric_id, user_id)
        return self.repository.get_rubric_with_criteria(rubric_id)
    
    def create_evaluation_rubric(
        self,
        user_id: UUID,
        name: str
    ):
        """Create a standard evaluation rubric with semantic, coverage, and BM25 criteria."""
        criteria = [
            {"criterion": "Semantic Similarity", "weight_percentage": 40},
            {"criterion": "Coverage", "weight_percentage": 35},
            {"criterion": "BM25 Relevance", "weight_percentage": 25},
        ]
        return self.create_rubric_with_criteria(
            user_id=user_id,
            name=name,
            criteria=criteria,
            description="Standard evaluation rubric with semantic, coverage, and BM25 criteria",
            rubric_type="custom",
        )
