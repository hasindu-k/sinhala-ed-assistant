# app/services/evaluation/question_paper_service.py

from typing import Optional, List, Dict
from uuid import UUID
from sqlalchemy.orm import Session

from app.services.evaluation.question_paper_repository import QuestionPaperRepository


class QuestionPaperService:
    """Business logic for question paper management."""
    
    def __init__(self, db: Session):
        self.repository = QuestionPaperRepository(db)
    
    def create_question_paper(
        self,
        evaluation_session_id: UUID,
        resource_id: UUID,
        extracted_text: Optional[str] = None
    ):
        """Create a question paper entry."""
        return self.repository.create_question_paper(
            evaluation_session_id=evaluation_session_id,
            resource_id=resource_id,
            extracted_text=extracted_text
        )
    
    def get_question_paper(self, question_paper_id: UUID):
        """Get question paper by ID."""
        return self.repository.get_question_paper(question_paper_id)
    
    def get_question_papers_by_evaluation_session(self, evaluation_session_id: UUID) -> List:
        """Get all question papers for an evaluation session."""
        return self.repository.get_question_papers_by_evaluation_session(evaluation_session_id)
    
    def create_question(
        self,
        question_paper_id: UUID,
        question_number: str,
        question_text: str,
        max_marks: int
    ):
        """Create a main question."""
        return self.repository.create_question(
            question_paper_id=question_paper_id,
            question_number=question_number,
            question_text=question_text,
            max_marks=max_marks
        )
    
    def get_questions_by_paper(self, question_paper_id: UUID) -> List:
        """Get all questions for a question paper."""
        return self.repository.get_questions_by_paper(question_paper_id)
    
    def create_sub_question(
        self,
        question_id: UUID,
        label: str,
        sub_question_text: str,
        max_marks: int
    ):
        """Create a sub-question."""
        return self.repository.create_sub_question(
            question_id=question_id,
            label=label,
            sub_question_text=sub_question_text,
            max_marks=max_marks
        )
    
    def get_sub_questions_by_question(self, question_id: UUID) -> List:
        """Get all sub-questions for a main question."""
        return self.repository.get_sub_questions_by_question(question_id)
    
    def create_structured_questions(
        self,
        question_paper_id: UUID,
        structured_data: Dict
    ) -> List:
        """
        Create questions and sub-questions from structured data.
        
        structured_data format:
        {
            "Q01": {
                "question_text": "Main question text",
                "max_marks": 20,
                "sub_questions": {
                    "a": {"text": "Sub question a", "marks": 5},
                    "b": {"text": "Sub question b", "marks": 5}
                }
            }
        }
        """
        return self.repository.create_structured_questions(
            question_paper_id=question_paper_id,
            structured_data=structured_data
        )
    
    def get_question_paper_with_questions(self, question_paper_id: UUID) -> Optional[Dict]:
        """Get complete question paper with all questions and sub-questions."""
        return self.repository.get_question_paper_with_questions(question_paper_id)