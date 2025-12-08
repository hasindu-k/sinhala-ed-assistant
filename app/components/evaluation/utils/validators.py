# app/components/evaluation/utils/validators.py

from fastapi import HTTPException

def validate_student_answers(student_answers: dict, teacher_questions: dict):
    """
    Ensures student submits answers that exist in teacher's question set.
    """
    for qid in student_answers.keys():
        if qid not in teacher_questions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid question ID in student answers: {qid}"
            )
