from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.schemas.evaluation import (
    EvaluationSessionCreate,
    EvaluationSessionUpdate,
    EvaluationResourceAttach,
    PaperConfigCreate,
    PaperConfigUpdate,
    AnswerDocumentCreate,
)
from app.services.evaluation.evaluation_session_service import EvaluationSessionService
from app.services.evaluation.evaluation_resource_service import EvaluationResourceService
from app.services.evaluation.question_paper_service import QuestionPaperService
from app.services.evaluation.paper_config_service import PaperConfigService
from app.services.evaluation.answer_evaluation_service import AnswerEvaluationService
from app.services.chat_session_service import ChatSessionService
from app.services.resource_service import ResourceService
from app.components.document_processing.services.classifier_service import separate_paper_content
from app.components.document_processing.services.ocr_service import extract_and_clean_text_from_file
import logging

logger = logging.getLogger(__name__)


class EvaluationWorkflowService:
    """Orchestrates evaluation-related operations while keeping routers thin."""

    def __init__(self, db: Session):
        self.sessions = EvaluationSessionService(db)
        self.resources = EvaluationResourceService(db)
        self.question_papers = QuestionPaperService(db)
        self.paper_configs = PaperConfigService(db)
        self.answers = AnswerEvaluationService(db)
        self.chat_sessions = ChatSessionService(db)
        self.resource_files = ResourceService(db)

    # ------------------------------------------------------------------
    # Ownership helpers
    # ------------------------------------------------------------------
    def _ensure_chat_session_owner(self, session_id: UUID, user_id: UUID):
        if not self.chat_sessions.validate_ownership(session_id, user_id):
            raise PermissionError("You don't have permission to access this session")

    def _get_eval_session_with_owner_check(self, evaluation_id: UUID, user_id: UUID):
        eval_session = self.sessions.get_evaluation_session(evaluation_id)
        if not eval_session:
            raise ValueError("Evaluation session not found")
        self._ensure_chat_session_owner(eval_session.session_id, user_id)
        return eval_session

    def _ensure_resource_owner(self, resource_id: UUID, user_id: UUID):
        # Will raise PermissionError / ValueError if unauthorized or missing
        self.resource_files.get_resource_with_ownership_check(resource_id, user_id)

    def _ensure_answer_owner(self, answer_id: UUID, user_id: UUID):
        answer_doc = self.answers.get_answer_document(answer_id)
        if not answer_doc:
            raise ValueError("Answer document not found")
        self._get_eval_session_with_owner_check(answer_doc.evaluation_session_id, user_id)
        return answer_doc

    def create_session(self, payload: EvaluationSessionCreate, user_id: UUID):
        self._ensure_chat_session_owner(payload.session_id, user_id)
        return self.sessions.create_evaluation_session(
            session_id=payload.session_id,
            rubric_id=payload.rubric_id,
        )

    def list_sessions(self, user_id: UUID, session_id: Optional[UUID] = None) -> List:
        if session_id:
            self._ensure_chat_session_owner(session_id, user_id)
            return self.sessions.get_evaluation_sessions_by_chat_session(session_id)

        # Filter to only the caller's chat sessions
        sessions = self.sessions.list_all_sessions()
        return [s for s in sessions if self.chat_sessions.validate_ownership(s.session_id, user_id)]

    def get_session(self, evaluation_id: UUID, user_id: UUID):
        return self._get_eval_session_with_owner_check(evaluation_id, user_id)

    def update_session(self, evaluation_id: UUID, payload: EvaluationSessionUpdate, user_id: UUID):
        self._get_eval_session_with_owner_check(evaluation_id, user_id)
        return self.sessions.update_evaluation_session(
            evaluation_session_id=evaluation_id,
            status=payload.status.value if payload.status else None,
            rubric_id=payload.rubric_id,
        )

    def attach_resource(self, evaluation_id: UUID, payload: EvaluationResourceAttach, user_id: UUID):
        self._get_eval_session_with_owner_check(evaluation_id, user_id)
        self._ensure_resource_owner(payload.resource_id, user_id)
        return self.resources.attach_resource(
            evaluation_session_id=evaluation_id,
            resource_id=payload.resource_id,
            role=payload.role.value,
        )

    def parse_question_paper(self, evaluation_id: UUID, user_id: UUID):
        """
        Parse question paper by extracting text and structuring content.
        Uses OCR if needed and AI-based content separation.
        """
        self._get_eval_session_with_owner_check(evaluation_id, user_id)

        # Check if already parsed
        question_papers = self.question_papers.get_question_papers_by_evaluation_session(evaluation_id)
        if question_papers:
            return self.question_papers.get_question_paper_with_questions(question_papers[0].id)

        # Get attached question paper resource
        resources = self.resources.get_resources_by_role(
            evaluation_session_id=evaluation_id,
            role="question_paper",
        )
        if not resources:
            raise ValueError("No question paper resource attached to this evaluation session")

        self._ensure_resource_owner(resources[0].resource_id, user_id)
        
        # Get resource file
        resource = self.resource_files.get_resource_with_ownership_check(
            resources[0].resource_id, 
            user_id
        )
        
        if not resource.storage_path:
            raise ValueError("Resource file not found on disk")

        # Extract and clean text from file
        try:
            cleaned_text, page_count = extract_and_clean_text_from_file(resource.storage_path)
            logger.info("Extracted %s characters from %d0 pages in question paper", len(cleaned_text), page_count)
            
        except Exception as e:
            logger.error(f"Failed to extract text from resource {resource.id}: {e}", exc_info=True)
            raise ValueError(f"Failed to extract text from question paper: {e}")

        # Parse and structure content using AI
        try:
            paper_metadata, instructions, paper_structure = separate_paper_content(cleaned_text)
            logger.info(f"Parsed question paper structure: {len(paper_structure)} papers found")
        except Exception as e:
            logger.error(f"Failed to parse paper structure: {e}", exc_info=True)
            raise ValueError(f"Failed to parse question paper structure: {e}")

        # Create question paper entry
        question_paper = self.question_papers.create_question_paper(
            evaluation_session_id=evaluation_id,
            resource_id=resources[0].resource_id,
            extracted_text=cleaned_text,
        )

        # Create structured questions from parsed data
        try:
            # Process each paper (Paper_I, Paper_II, etc.)
            for paper_key, paper_data in paper_structure.items():
                questions_dict = paper_data.get("questions", {})
                
                if questions_dict:
                    # Transform structure to match create_structured_questions format
                    structured_data = {}
                    for q_num, q_data in questions_dict.items():
                        structured_data[q_num] = {
                            "question_text": q_data.get("text", ""),
                            "max_marks": q_data.get("marks"),
                            "sub_questions": {}
                        }
                        
                        # Handle sub-questions if present
                        sub_questions = q_data.get("sub_questions", {})
                        for sq_label, sq_data in sub_questions.items():
                            structured_data[q_num]["sub_questions"][sq_label] = {
                                "text": sq_data.get("text", ""),
                                "marks": sq_data.get("marks")
                            }
                    
                    # Create questions in database
                    if structured_data:
                        self.question_papers.create_structured_questions(
                            question_paper_id=question_paper.id,
                            structured_data=structured_data
                        )
                        logger.info(f"Created {len(structured_data)} questions for {paper_key}")
        
        except Exception as e:
            logger.error(f"Failed to create structured questions: {e}", exc_info=True)
            # Don't fail the entire operation if question creation fails
            # The paper is still parsed and text is saved

        # Return complete question paper with questions
        return self.question_papers.get_question_paper_with_questions(question_paper.id)

    def get_parsed_questions(self, evaluation_id: UUID, user_id: UUID):
        self._get_eval_session_with_owner_check(evaluation_id, user_id)
        question_papers = self.question_papers.get_question_papers_by_evaluation_session(evaluation_id)
        if not question_papers:
            return []

        return self.question_papers.get_questions_by_paper(question_papers[0].id)

    def save_paper_config(self, evaluation_id: UUID, payload: PaperConfigCreate, user_id: UUID):
        self._get_eval_session_with_owner_check(evaluation_id, user_id)
        return self.paper_configs.save_config(
            evaluation_session_id=evaluation_id,
            paper_part=payload.paper_part,
            subject_name=payload.subject_name,
            medium=payload.medium,
            total_marks=payload.total_marks,
            weightage=float(payload.weightage) if payload.weightage is not None else None,
            total_main_questions=payload.total_main_questions,
            selection_rules=payload.selection_rules,
        )

    def get_paper_config(self, evaluation_id: UUID, user_id: UUID):
        self._get_eval_session_with_owner_check(evaluation_id, user_id)
        return self.paper_configs.get_config(evaluation_id)

    def confirm_paper_config(self, evaluation_id: UUID, payload: PaperConfigUpdate, user_id: UUID):
        """Update provided fields and confirm the paper configuration for an evaluation session."""
        self._get_eval_session_with_owner_check(evaluation_id, user_id)
        return self.paper_configs.confirm_config(
            evaluation_session_id=evaluation_id,
            paper_part=payload.paper_part,
            subject_name=payload.subject_name,
            medium=payload.medium,
            total_marks=payload.total_marks,
            weightage=float(payload.weightage) if payload.weightage is not None else None,
            total_main_questions=payload.total_main_questions,
            selection_rules=payload.selection_rules,
        )

    def register_answer_document(self, evaluation_id: UUID, payload: AnswerDocumentCreate, user_id: UUID):
        self._get_eval_session_with_owner_check(evaluation_id, user_id)
        self._ensure_resource_owner(payload.resource_id, user_id)
        return self.answers.create_answer_document(
            evaluation_session_id=evaluation_id,
            resource_id=payload.resource_id,
            student_identifier=payload.student_identifier,
        )

    def list_answer_documents(self, evaluation_id: UUID, user_id: UUID):
        self._get_eval_session_with_owner_check(evaluation_id, user_id)
        return self.answers.get_answer_documents_by_evaluation_session(evaluation_id)

    def evaluate_answer(self, answer_id: UUID, user_id: UUID):
        self._ensure_answer_owner(answer_id, user_id)
        existing = self.answers.get_evaluation_result_by_answer_document(answer_id)
        if existing:
            return existing
        return self.answers.create_evaluation_result(answer_document_id=answer_id)

    def get_evaluation_result(self, answer_id: UUID, user_id: UUID):
        self._ensure_answer_owner(answer_id, user_id)
        result = self.answers.get_evaluation_result_by_answer_document(answer_id)
        if not result:
            return None
        return self.answers.get_complete_evaluation_result(result.id)
