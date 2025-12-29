# app/repositories/evaluation/question_paper_repository.py

from typing import Optional, List, Dict
from uuid import UUID
from sqlalchemy.orm import Session

from app.shared.models.question_papers import QuestionPaper, Question, SubQuestion


class QuestionPaperRepository:
    """Data access layer for question paper models."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_question_paper(
        self,
        evaluation_session_id: UUID,
        resource_id: UUID,
        extracted_text: Optional[str] = None
    ) -> QuestionPaper:
        """Create a question paper entry."""
        question_paper = QuestionPaper(
            evaluation_session_id=evaluation_session_id,
            resource_id=resource_id,
            extracted_text=extracted_text
        )
        self.db.add(question_paper)
        self.db.commit()
        self.db.refresh(question_paper)
        return question_paper
    
    def get_question_paper(self, question_paper_id: UUID) -> Optional[QuestionPaper]:
        """Get question paper by ID."""
        return self.db.query(QuestionPaper).filter(
            QuestionPaper.id == question_paper_id
        ).first()
    
    def get_question_papers_by_evaluation_session(
        self,
        evaluation_session_id: UUID
    ) -> List[QuestionPaper]:
        """Get all question papers for an evaluation session."""
        return self.db.query(QuestionPaper).filter(
            QuestionPaper.evaluation_session_id == evaluation_session_id
        ).all()
    
    def create_question(
        self,
        question_paper_id: UUID,
        question_number: str,
        question_text: str,
        max_marks: Optional[int] = None,
        shared_stem: Optional[str] = None,
        inherits_shared_stem_from: Optional[str] = None,
    ) -> Question:
        """Create a main question."""
        question = Question(
            question_paper_id=question_paper_id,
            question_number=question_number,
            question_text=question_text,
            max_marks=max_marks,
            shared_stem=shared_stem,
            inherits_shared_stem_from=inherits_shared_stem_from,
        )
        self.db.add(question)
        self.db.commit()
        self.db.refresh(question)
        return question
    
    def get_questions_by_paper(self, question_paper_id: UUID) -> List[Question]:
        """Get all questions for a question paper."""
        return self.db.query(Question).filter(
            Question.question_paper_id == question_paper_id
        ).order_by(Question.question_number).all()
    
    def create_sub_question(
        self,
        question_id: UUID,
        label: str,
        sub_question_text: str,
        max_marks: Optional[int] = None,
        parent_sub_question_id: Optional[UUID] = None,
    ) -> SubQuestion:
        """Create a sub-question."""
        sub_question = SubQuestion(
            question_id=question_id,
            label=label,
            sub_question_text=sub_question_text,
            max_marks=max_marks,
            parent_sub_question_id=parent_sub_question_id
        )
        self.db.add(sub_question)
        self.db.commit()
        self.db.refresh(sub_question)
        return sub_question
    
    def get_sub_questions_by_question(self, question_id: UUID) -> List[SubQuestion]:
        """Get all sub-questions for a main question."""
        return self.db.query(SubQuestion).filter(
            SubQuestion.question_id == question_id
        ).order_by(SubQuestion.label).all()
    

    def create_structured_questions(
        self,
        question_paper_id: UUID,
        structured_data: Dict
    ) -> List[Question]:
        """
        Create questions and sub-questions from structured data.
        """
        created_questions = []
        
        for q_num, q_data in structured_data.items():
            # Handle options for MCQs by appending to text if present
            q_text = q_data.get("text", "")
            if "options" in q_data and isinstance(q_data["options"], list):
                options_text = "\n".join(q_data["options"])
                q_text = f"{q_text}\n\nOptions:\n{options_text}"
            
            # Create main question
            question = self.create_question(
                question_paper_id=question_paper_id,
                question_number=str(q_num),
                question_text=q_text,
                max_marks=q_data.get("marks"),
                shared_stem=q_data.get("shared_stem"),
                inherits_shared_stem_from=str(q_data.get("inherits_shared_stem_from")) if q_data.get("inherits_shared_stem_from") else None
            )
            created_questions.append(question)
            
            # Handle sub-questions
            if "sub_questions" in q_data and isinstance(q_data["sub_questions"], dict):
                self._create_recursive_sub_questions(
                    question.id, 
                    q_data["sub_questions"]
                )
                
        return created_questions

    def _create_recursive_sub_questions(
        self, 
        question_id: UUID, 
        sub_questions_data: Dict, 
        parent_sub_question_id: Optional[UUID] = None
    ):
        for label, sub_data in sub_questions_data.items():
            # Create sub-question
            sub_q = self.create_sub_question(
                question_id=question_id,
                label=str(label),
                sub_question_text=sub_data.get("text", ""),
                max_marks=sub_data.get("marks"),
                parent_sub_question_id=parent_sub_question_id
            )
            
            # Check for nested sub-questions (if any)
            if "sub_questions" in sub_data and isinstance(sub_data["sub_questions"], dict):
                 self._create_recursive_sub_questions(
                    question_id,
                    sub_data["sub_questions"],
                    parent_sub_question_id=sub_q.id
                )

    def get_question_paper_with_questions(
        self,
        question_paper_id: UUID
    ) -> Optional[Dict]:
        """Get complete question paper with all questions and sub-questions in hierarchical structure."""
        paper = self.get_question_paper(question_paper_id)
        if not paper:
            return None
        
        questions = self.get_questions_by_paper(question_paper_id)
        
        def build_sub_question_tree(sub_questions: List[SubQuestion], parent_id=None):
            """Recursively build hierarchical sub-question structure."""
            children = []
            for sq in sub_questions:
                if sq.parent_sub_question_id == parent_id:
                    child_tree = {
                        "id": sq.id,
                        "label": sq.label,
                        "text": sq.sub_question_text,
                        "max_marks": sq.max_marks,
                        "parent_sub_question_id": sq.parent_sub_question_id,
                        "children": build_sub_question_tree(sub_questions, sq.id)
                    }
                    children.append(child_tree)
            return children
        
        result = {
            "id": paper.id,
            "evaluation_session_id": paper.evaluation_session_id,
            "resource_id": paper.resource_id,
            "extracted_text": paper.extracted_text,
            "created_at": paper.created_at,
            "questions": []
        }
        
        for question in questions:
            sub_questions = self.get_sub_questions_by_question(question.id)
            result["questions"].append({
                "id": question.id,
                "question_number": question.question_number,
                "question_text": question.question_text,
                "max_marks": question.max_marks,
                "sub_questions": build_sub_question_tree(sub_questions)
            })
        
        return result
