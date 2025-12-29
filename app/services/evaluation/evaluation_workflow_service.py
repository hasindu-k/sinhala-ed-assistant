# app/services/evaluation/evaluation_workflow_service.py

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
from app.components.document_processing.services.classifier_service import extract_complete_exam_data
from app.components.document_processing.services.ocr_service import extract_and_clean_text_from_file
import logging

logger = logging.getLogger(__name__)


class EvaluationWorkflowService:
    """Orchestrates evaluation-related operations while keeping routers thin."""

    def __init__(self, db: Session):
        self.db = db
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
        
        # Get Chat Session to retrieve attached resources
        chat_session = self.chat_sessions.get_session(payload.session_id)
        if not chat_session:
            raise ValueError("Chat session not found")
            
        # Determine Rubric ID: Payload > Chat Session > None
        rubric_id = payload.rubric_id or chat_session.rubric_id
        
        session = self.sessions.create_evaluation_session(
            session_id=payload.session_id,
            rubric_id=rubric_id,
        )
        
        return session


    def start_evaluation_session(self, chat_session_id: UUID, answer_resource_ids: List[UUID], user_id: UUID):
        """
        Creates a session, attaches active context + answers, and starts processing.
        """
        # 1. Create Session (reuses logic to attach Rubric, Syllabus, QP)
        payload = EvaluationSessionCreate(session_id=chat_session_id)
        session = self.create_session(payload, user_id)
        
        # 2. Attach Answer Scripts
        for resource_id in answer_resource_ids:
            self._ensure_resource_owner(resource_id, user_id)
            # Create Answer Document
            self.answers.create_answer_document(
                evaluation_session_id=session.id,
                resource_id=resource_id,
                student_identifier=f"Student-{resource_id}" # Placeholder
            )
            
        # 3. Update Status to Processing
        self.sessions.update_evaluation_session(session.id, status="processing")
        
        # 4. Trigger Async Processing (Placeholder for now)
        # TODO: Enqueue background task for OCR and Evaluation
        
        return session

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
            status=payload.status,
            rubric_id=payload.rubric_id,
        )



    def parse_question_paper(self, session_id: UUID, user_id: UUID):
        """
        Parse question paper by extracting text and structuring content.
        Uses OCR if needed and AI-based content separation.
        """
        # Verify ownership and get session
        self._ensure_chat_session_owner(session_id, user_id)

        # Check if already parsed for this chat session
        question_papers = self.question_papers.get_question_papers_by_chat_session(session_id)
        if question_papers:
            return self.question_papers.get_question_paper_with_questions(question_papers[0].id)

        # Get attached question paper resource from Chat Session
        from app.shared.models.session_resources import SessionResource
        session_resource = self.db.query(SessionResource).filter(
            SessionResource.session_id == session_id,
            SessionResource.label == "question_paper"
        ).first()

        if not session_resource:
            raise ValueError("No question paper resource attached to this chat session")

        self._ensure_resource_owner(session_resource.resource_id, user_id)
        
        # Get resource file
        resource = self.resource_files.get_resource_with_ownership_check(
            session_resource.resource_id, 
            user_id
        )
        
        if not resource.storage_path:
            raise ValueError("Resource file not found on disk")

        # Extract and clean text from file
        try:
            cleaned_text, page_count = extract_and_clean_text_from_file(resource.storage_path)
            logger.info("Extracted %s characters from %d pages in question paper", len(cleaned_text), page_count)

        # Persist OCR text back to ResourceFile (CRITICAL)
            resource.extracted_text = cleaned_text
            self.resource_files.db.commit()

        except Exception as e:
            logger.error(f"Failed to extract text from resource {resource.id}: {e}", exc_info=True)
            raise ValueError(f"Failed to extract text from question paper: {e}")

        # Parse and structure content using AI
        try:
            # extract with paper config and paper structure separation
            result = extract_complete_exam_data(cleaned_text)

            if not isinstance(result, dict):
                raise ValueError("Gemini parser returned invalid structure")

            if not any(
                isinstance(v, dict) and "questions" in v
                for v in result.values()
            ):
                raise ValueError("No questions detected in parsed paper")

            
            logger.info(f"Parsed question paper structure: {len(result)} papers found")
            logger.debug(f"Parsed structure details: {result}")
        except Exception as e:
            logger.error(f"Failed to parse paper structure: {e}", exc_info=True)
            raise ValueError(f"Failed to parse question paper structure: {e}")
        
        # Create question paper entry linked to Chat Session
        question_paper = self.question_papers.create_question_paper(
            chat_session_id=session_id,
            resource_id=session_resource.resource_id,
            extracted_text=cleaned_text,
        )

        # Create structured questions from parsed data
        try:
            # Process each paper (Paper_I, Paper_II, etc.)
            for paper_key, paper_data in result.items():
                if not paper_data:
                    continue  # Skip null papers

                config = paper_data.get("config", {}) or {}

                # 1️⃣ Create PaperConfig for this paper linked to Chat Session
                self.paper_configs.save_config(
                    chat_session_id=session_id,
                    paper_part=paper_key,
                    subject_name=config.get("subject_detected"),
                    medium=config.get("medium"),
                    weightage=float(config.get("suggested_weightage")) if config.get("suggested_weightage") is not None else None,
                    total_main_questions=config.get("total_questions_available"),
                    selection_rules=config.get("selection_rules"),
                )

                # 2️⃣ Create Questions
                questions_dict = paper_data.get("questions", {}) or {}
                for q_num, q_data in questions_dict.items():
                    question = self.question_papers.create_question(
                        question_paper_id=question_paper.id,
                        question_number=q_num,
                        question_text=q_data.get("text"),
                        max_marks=q_data.get("marks"),
                        shared_stem=q_data.get("shared_stem"),
                        inherits_shared_stem_from=q_data.get("inherits_shared_stem_from")
                    )

                    # 3️⃣ Create SubQuestions (Recursive)
                    def create_sub_tree(parent_q_id, sub_data, parent_sq_id=None):
                        if not sub_data:
                            return
                        for label, data in sub_data.items():
                            sq = self.question_papers.create_sub_question(
                                question_id=parent_q_id,
                                label=label,
                                sub_question_text=data.get("text"),
                                max_marks=data.get("marks"),
                                parent_sub_question_id=parent_sq_id
                            )
                            # Recurse for children
                            if "sub_questions" in data:
                                create_sub_tree(parent_q_id, data["sub_questions"], sq.id)

                    sub_questions = q_data.get("sub_questions", {}) or {}
                    create_sub_tree(question.id, sub_questions)

                logger.info(f"Created {len(questions_dict)} questions for {paper_key}")

        except Exception as e:
            logger.error(f"Failed to create structured questions: {e}", exc_info=True)
            # Don't fail the entire operation if question creation fails
            # The paper is still parsed and text is saved

        # Return complete question paper with questions
        return self.question_papers.get_question_paper_with_questions(question_paper.id)

    def get_parsed_questions(self, session_id: UUID, user_id: UUID):
        self._ensure_chat_session_owner(session_id, user_id)
        question_papers = self.question_papers.get_question_papers_by_chat_session(session_id)
        if not question_papers:
            return []

        return self.question_papers.get_questions_by_paper(question_papers[0].id)

    def save_paper_config(self, session_id: UUID, payload: PaperConfigCreate, user_id: UUID):
        self._ensure_chat_session_owner(session_id, user_id)
        return self.paper_configs.save_config(
            chat_session_id=session_id,
            paper_part=payload.paper_part,
            subject_name=payload.subject_name,
            medium=payload.medium,
            weightage=float(payload.weightage) if payload.weightage is not None else None,
            total_main_questions=payload.total_main_questions,
            selection_rules=payload.selection_rules,
        )

    def get_paper_config(self, session_id: UUID, user_id: UUID):
        self._ensure_chat_session_owner(session_id, user_id)
        return self.paper_configs.get_config(chat_session_id=session_id)

    def confirm_paper_config(self, session_id: UUID, payload: PaperConfigUpdate, user_id: UUID):
        """Update provided fields and confirm the paper configuration for an evaluation session."""
        self._ensure_chat_session_owner(session_id, user_id)
        
        config = self.paper_configs.confirm_config(
            chat_session_id=session_id,
            paper_part=payload.paper_part,
            subject_name=payload.subject_name,
            medium=payload.medium,
            weightage=float(payload.weightage) if payload.weightage is not None else None,
            total_main_questions=payload.total_main_questions,
            selection_rules=payload.selection_rules,
        )
        
        # Update Global Context with this new configuration
        from app.services.evaluation.user_context_service import UserContextService
        context_service = UserContextService(self.db)
        # We need to serialize the config to a list of dicts as expected by update_paper_config
        # Since we might have multiple parts (Paper I, Paper II), we should ideally fetch all configs for this session
        # For now, we'll just save this specific confirmed config as a single-item list or append logic if needed.
        # A simpler approach for the MVP is to save the current confirmed config as the "active" one.
        
        config_data = [{
            "paper_part": config.paper_part,
            "subject_name": config.subject_name,
            "medium": config.medium,
            "weightage": float(config.weightage) if config.weightage else None,
            "total_main_questions": config.total_main_questions,
            "selection_rules": config.selection_rules
        }]
        context_service.update_paper_config(user_id, config_data)
        
        return config

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
        """Evaluate answer with recursive sub-question support."""
        answer_doc = self._ensure_answer_owner(answer_id, user_id)

        # Check if already evaluated
        existing = self.answers.get_evaluation_result_by_answer_document(answer_id)
        if existing:
            return existing

        # Get the answer document with OCR text
        answer_resource = self.resource_files.get_resource(answer_doc.resource_id)
        if not answer_resource:
            raise ValueError("Answer resource not found")

        # OCR the answer script if not already done
        if not answer_resource.extracted_text:
            ocr_text, _ = extract_and_clean_text_from_file(answer_resource.storage_path)
            # Update the resource with extracted text
            self.resource_files.update_resource_extracted_text(answer_resource.id, ocr_text)
        else:
            ocr_text = answer_resource.extracted_text
        
        # Get Evaluation Session to find Chat Session
        eval_session = self.sessions.get_evaluation_session(answer_doc.evaluation_session_id)
        if not eval_session:
            raise ValueError("Evaluation session not found")

        # Get question paper hierarchy from Chat Session
        question_papers = self.question_papers.get_question_papers_by_chat_session(
            eval_session.session_id
        )
        if not question_papers:
            raise ValueError("Question paper not found for this chat session")

        question_paper = question_papers[0]  # Take the first question paper

        question_hierarchy = self.question_papers.get_question_paper_with_questions(
            question_paper.id
        )
        if not question_hierarchy:
            raise ValueError("Question hierarchy not found")

        # Parse answers and build recursive answer tree
        from app.utils.answer_parser import parse_answer_text, map_answers_to_sub_questions

        parsed_answers = parse_answer_text(ocr_text)
        answer_mapping = map_answers_to_sub_questions(parsed_answers, question_hierarchy['questions'])

        # Extract only leaf-level answers for evaluation
        from app.utils.numbering import get_leaf_sub_questions

        leaf_answers = {}
        for question in question_hierarchy['questions']:
            leaves = get_leaf_sub_questions(question['sub_questions'])
            for leaf in leaves:
                leaf_answers[str(leaf['id'])] = answer_mapping.get(str(leaf['id']), "")

        # Create evaluation result (Placeholder for actual AI evaluation)
        # TODO: Implement AI grading using the Rubric and Parsed Answers
        evaluation_result = self.answers.create_evaluation_result(
            answer_document_id=answer_id,
            total_score=None, # Pending evaluation
            overall_feedback="Evaluation pending implementation."
        )
        
        return evaluation_result


    def get_evaluation_result(self, answer_id: UUID, user_id: UUID):
        self._ensure_answer_owner(answer_id, user_id)
        result = self.answers.get_evaluation_result_by_answer_document(answer_id)
        if not result:
            return None
        return self.answers.get_complete_evaluation_result(result.id)
