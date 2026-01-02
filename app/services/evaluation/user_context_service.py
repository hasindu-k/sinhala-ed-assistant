
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.shared.models.user_evaluation_context import UserEvaluationContext
from app.shared.models.resource_file import ResourceFile
from app.shared.models.rubrics import Rubric

class UserContextService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_context(self, user_id: UUID) -> UserEvaluationContext:
        context = self.db.query(UserEvaluationContext).filter(UserEvaluationContext.user_id == user_id).first()
        if not context:
            context = UserEvaluationContext(user_id=user_id)
            self.db.add(context)
            self.db.commit()
            self.db.refresh(context)
        return context

    def update_syllabus(self, user_id: UUID, resource_id: UUID) -> UserEvaluationContext:
        context = self.get_or_create_context(user_id)
        context.active_syllabus_id = resource_id
        self.db.commit()
        self.db.refresh(context)
        return context

    def update_question_paper(self, user_id: UUID, resource_id: UUID) -> UserEvaluationContext:
        context = self.get_or_create_context(user_id)
        context.active_question_paper_id = resource_id
        self.db.commit()
        self.db.refresh(context)
        return context

    def update_rubric(self, user_id: UUID, rubric_id: UUID) -> UserEvaluationContext:
        context = self.get_or_create_context(user_id)
        # Check if it's a ResourceFile or a Rubric entity
        # For now, we assume if it comes from the upload endpoint, it's a ResourceFile
        # But the method signature just takes a UUID.
        # We'll try to find it in ResourceFile first.
        resource = self.db.query(ResourceFile).filter(ResourceFile.id == rubric_id).first()
        if resource:
            context.active_rubric_resource_id = rubric_id
            # Clear the structured rubric ID if we are switching to a file-based one
            # context.active_rubric_id = None 
        else:
            # Assume it's a structured Rubric
            context.active_rubric_id = rubric_id
            
        self.db.commit()
        self.db.refresh(context)
        return context

    def update_paper_config(self, user_id: UUID, config_data: list) -> UserEvaluationContext:
        context = self.get_or_create_context(user_id)
        context.active_paper_config = config_data
        self.db.commit()
        self.db.refresh(context)
        return context

    def get_context_details(self, user_id: UUID):
        context = self.get_or_create_context(user_id)
        
        syllabus = None
        if context.active_syllabus_id:
            syllabus = self.db.query(ResourceFile).filter(ResourceFile.id == context.active_syllabus_id).first()
            
        question_paper = None
        if context.active_question_paper_id:
            question_paper = self.db.query(ResourceFile).filter(ResourceFile.id == context.active_question_paper_id).first()
            
        rubric = None
        if context.active_rubric_resource_id:
             rubric = self.db.query(ResourceFile).filter(ResourceFile.id == context.active_rubric_resource_id).first()
        elif context.active_rubric_id:
            rubric = self.db.query(Rubric).filter(Rubric.id == context.active_rubric_id).first()
            
        return {
            "syllabus": syllabus,
            "question_paper": question_paper,
            "rubric": rubric,
            "paper_config": context.active_paper_config
        }
