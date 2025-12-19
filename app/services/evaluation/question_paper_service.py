# app/services/evaluation/question_paper_service.py

from typing import Optional, List, Dict
from uuid import UUID
from sqlalchemy.orm import Session

from app.shared.models.question_papers import QuestionPaper, Question, SubQuestion


def create_question_paper(
    *,
    db: Session,
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
    db.add(question_paper)
    db.commit()
    db.refresh(question_paper)
    return question_paper


def get_question_paper(
    *,
    db: Session,
    question_paper_id: UUID
) -> Optional[QuestionPaper]:
    """Get question paper by ID."""
    return db.query(QuestionPaper).filter(QuestionPaper.id == question_paper_id).first()


def get_question_papers_by_evaluation_session(
    *,
    db: Session,
    evaluation_session_id: UUID
) -> List[QuestionPaper]:
    """Get all question papers for an evaluation session."""
    return db.query(QuestionPaper).filter(
        QuestionPaper.evaluation_session_id == evaluation_session_id
    ).all()


def create_question(
    *,
    db: Session,
    question_paper_id: UUID,
    question_number: str,
    question_text: str,
    max_marks: int
) -> Question:
    """Create a main question."""
    question = Question(
        question_paper_id=question_paper_id,
        question_number=question_number,
        question_text=question_text,
        max_marks=max_marks
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def get_questions_by_paper(
    *,
    db: Session,
    question_paper_id: UUID
) -> List[Question]:
    """Get all questions for a question paper."""
    return db.query(Question).filter(
        Question.question_paper_id == question_paper_id
    ).order_by(Question.question_number).all()


def create_sub_question(
    *,
    db: Session,
    question_id: UUID,
    label: str,
    sub_question_text: str,
    max_marks: int
) -> SubQuestion:
    """Create a sub-question."""
    sub_question = SubQuestion(
        question_id=question_id,
        label=label,
        sub_question_text=sub_question_text,
        max_marks=max_marks
    )
    db.add(sub_question)
    db.commit()
    db.refresh(sub_question)
    return sub_question


def get_sub_questions_by_question(
    *,
    db: Session,
    question_id: UUID
) -> List[SubQuestion]:
    """Get all sub-questions for a main question."""
    return db.query(SubQuestion).filter(
        SubQuestion.question_id == question_id
    ).order_by(SubQuestion.label).all()


def create_structured_questions(
    *,
    db: Session,
    question_paper_id: UUID,
    structured_data: Dict
) -> List[Question]:
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
    questions = []
    
    for q_num, q_data in structured_data.items():
        question = create_question(
            db=db,
            question_paper_id=question_paper_id,
            question_number=q_num,
            question_text=q_data.get("question_text", ""),
            max_marks=q_data.get("max_marks", 0)
        )
        questions.append(question)
        
        sub_questions_data = q_data.get("sub_questions", {})
        for label, sq_data in sub_questions_data.items():
            create_sub_question(
                db=db,
                question_id=question.id,
                label=label,
                sub_question_text=sq_data.get("text", ""),
                max_marks=sq_data.get("marks", 0)
            )
    
    return questions


def get_question_paper_with_questions(
    *,
    db: Session,
    question_paper_id: UUID
) -> Optional[Dict]:
    """Get complete question paper with all questions and sub-questions."""
    paper = get_question_paper(db=db, question_paper_id=question_paper_id)
    if not paper:
        return None
    
    questions = get_questions_by_paper(db=db, question_paper_id=question_paper_id)
    
    result = {
        "id": paper.id,
        "evaluation_session_id": paper.evaluation_session_id,
        "resource_id": paper.resource_id,
        "extracted_text": paper.extracted_text,
        "created_at": paper.created_at,
        "questions": []
    }
    
    for question in questions:
        sub_questions = get_sub_questions_by_question(db=db, question_id=question.id)
        result["questions"].append({
            "id": question.id,
            "question_number": question.question_number,
            "question_text": question.question_text,
            "max_marks": question.max_marks,
            "sub_questions": [
                {
                    "id": sq.id,
                    "label": sq.label,
                    "text": sq.sub_question_text,
                    "max_marks": sq.max_marks
                }
                for sq in sub_questions
            ]
        })
    
    return result