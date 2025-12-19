# app/services/evaluation/rubric_service.py

from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.evaluation.rubric_repository import RubricRepository


class RubricService:
    """Business logic for rubric management."""
    
    def __init__(self, db: Session):
        self.repository = RubricRepository(db)
    
    def create_rubric(
        self,
        user_id: UUID,
        name: str,
        description: Optional[str] = None
    ):
        """Create a new rubric."""
        return self.repository.create_rubric(
            user_id=user_id,
            name=name,
            description=description
        )
    
    def get_rubric(self, rubric_id: UUID):
        """Get rubric by ID."""
        return self.repository.get_rubric(rubric_id)
    
    def get_rubrics_by_user(self, user_id: UUID) -> List:
        """Get all rubrics for a user."""
        return self.repository.get_rubrics_by_user(user_id)
    
    def update_rubric(
        self,
        rubric_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None
    ):
        """Update rubric."""
        return self.repository.update_rubric(
            rubric_id=rubric_id,
            name=name,
            description=description
        )
    
    def delete_rubric(self, rubric_id: UUID) -> bool:
        """Delete rubric."""
        return self.repository.delete_rubric(rubric_id)
    
    def create_rubric_criterion(
        self,
        rubric_id: UUID,
        criterion_name: str,
        description: Optional[str] = None,
        weight: int = 0
    ):
        """Create a rubric criterion."""
        return self.repository.create_rubric_criterion(
            rubric_id=rubric_id,
            criterion_name=criterion_name,
            description=description,
            weight=weight
        )
    
    def get_rubric_criteria(self, rubric_id: UUID) -> List:
        """Get all criteria for a rubric."""
        return self.repository.get_rubric_criteria(rubric_id)
    
    def create_rubric_with_criteria(
        self,
        user_id: UUID,
        name: str,
        criteria: List[dict],
        description: Optional[str] = None
    ):
        """
        Create a complete rubric with criteria.
        
        criteria format:
        [
            {
                "criterion_name": "Content",
                "description": "Accuracy of content",
                "weight": 40
            }
        ]
        """
        rubric = self.repository.create_rubric(
            user_id=user_id,
            name=name,
            description=description
        )
        
        for criterion_data in criteria:
            self.repository.create_rubric_criterion(
                rubric_id=rubric.id,
                criterion_name=criterion_data["criterion_name"],
                description=criterion_data.get("description"),
                weight=criterion_data.get("weight", 0)
            )
        
        return rubric
    
    def get_rubric_with_criteria(self, rubric_id: UUID) -> Optional[dict]:
        """Get rubric with all its criteria."""
        return self.repository.get_rubric_with_criteria(rubric_id)
    
    def create_evaluation_rubric(
        self,
        user_id: UUID,
        name: str
    ):
        """Create a standard evaluation rubric with semantic, coverage, and BM25 criteria."""
        criteria = [
            {
                "criterion_name": "Semantic Similarity",
                "description": "How well the answer matches the reference semantically",
                "weight": 40
            },
            {
                "criterion_name": "Coverage",
                "description": "How comprehensively the answer covers the question",
                "weight": 35
            },
            {
                "criterion_name": "BM25 Relevance",
                "description": "How relevant the answer is based on BM25 scoring",
                "weight": 25
            }
        ]
        
        return self.create_rubric_with_criteria(
            user_id=user_id,
            name=name,
            criteria=criteria,
            description="Standard evaluation rubric with semantic, coverage, and BM25 criteria"
        )
