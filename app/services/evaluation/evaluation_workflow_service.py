# app/services/evaluation/evaluation_workflow_service.py

import re
from typing import Optional, List, Union
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
from app.components.document_processing.services.classifier_service import extract_complete_exam_data, fix_sinhala_ocr, map_student_answers
from app.components.document_processing.services.ocr_service import extract_and_clean_text_from_file
from app.shared.models.answer_evaluation import QuestionScore
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

    def _normalize_question_number(self, q_num: str) -> str:
        """Normalize question number (e.g. '1.', 'Q1' -> '1')"""
        if not q_num:
            return q_num
        # Remove parens, dots
        clean = re.sub(r'[().]', '', str(q_num)).strip()
        # Remove "Q" or "q" prefix if followed by number
        clean = re.sub(r'^[Qq](\d+)', r'\1', clean)
        return clean

    def _normalize_sub_question_label(self, label: str) -> str:
        """Normalize sub-question label (e.g. '(a)', 'a.' -> 'a')"""
        if not label:
            return label
        # Remove parens, dots and convert to lowercase
        clean = re.sub(r'[().]', '', str(label)).strip().lower()
        return clean

    def _resolve_session_id(self, session_id: UUID) -> UUID:
        """Resolves Evaluation Session ID to Chat Session ID if applicable."""
        eval_session = self.sessions.get_evaluation_session(session_id)
        if eval_session:
            return eval_session.session_id
        return session_id

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


    def initialize_evaluation_session(self, chat_session_id: UUID, answer_resource_ids: List[UUID], user_id: UUID):
        """
        Creates a session, attaches active context + answers, and sets status to processing.
        Returns the session immediately.
        """
        # 1. Create Session (reuses logic to attach Rubric, Syllabus, QP)
        # Check if session already exists for this chat_session (created by process_documents)
        sessions = self.sessions.get_evaluation_sessions_by_chat_session(chat_session_id)
        if sessions:
            session = sessions[0]
        else:
            payload = EvaluationSessionCreate(session_id=chat_session_id)
            session = self.create_session(payload, user_id)
        
        # 2. Attach Answer Scripts
        for resource_id in answer_resource_ids:
            self._ensure_resource_owner(resource_id, user_id)
            
            # Check if Answer Document already exists
            existing_ad = self.answers.get_answer_document_by_session_and_resource(session.id, resource_id)
            
            if not existing_ad:
                # Create Answer Document only if it doesn't exist
                self.answers.create_answer_document(
                    evaluation_session_id=session.id,
                    resource_id=resource_id,
                    student_identifier=f"Student-{resource_id}" # Placeholder
                )
            
        # 3. Update Status to Processing
        self.sessions.update_evaluation_session(session.id, status="processing")
        
        return session

    def execute_evaluation_process(self, session_id: UUID, answer_resource_ids: List[UUID], user_id: UUID):
        """
        Performs the actual heavy lifting of evaluation.
        Should be called in a background task.
        """
        try:
            logger.info(f"Starting background evaluation for session {session_id}")
            
            for resource_id in answer_resource_ids:
                # Find the answer document we just ensured exists
                ad = self.answers.get_answer_document_by_session_and_resource(session_id, resource_id)
                if ad:
                    try:
                        logger.info(f"Triggering evaluation for answer document {ad.id}...")
                        self.evaluate_answer(ad.id, user_id)
                        logger.info(f"Evaluation finished for answer document {ad.id}.")
                    except Exception as e:
                        logger.error(f"Failed to evaluate answer {ad.id}: {e}")
                        # Continue with others
            
            self.sessions.update_evaluation_session(session_id, status="completed")
            logger.info(f"Background evaluation completed for session {session_id}")
            
        except Exception as e:
            logger.error(f"Critical error in background evaluation: {e}")
            self.sessions.update_evaluation_session(session_id, status="failed")

    def execute_evaluation_process_generator(self, session_id: UUID, answer_resource_ids: List[UUID], user_id: UUID):
        """
        Generator that yields progress updates for evaluation process.
        Yields JSON strings formatted for SSE.
        """
        import json
        
        total_docs = len(answer_resource_ids)
        current_doc_index = 0
        
        def make_event(msg, progress=None, status="processing", detail=None, stage="initializing"):
            nonlocal current_doc_index
            if progress is None:
                # Calculate progress based on completed docs + current step estimate
                # This is a rough estimate
                base_progress = int((current_doc_index / total_docs) * 100) if total_docs > 0 else 0
                progress = base_progress
            
            data = {
                "progress": progress,
                "message": msg,
                "status": status,
                "stage": stage,
                "detail": detail
            }
            return json.dumps(data, default=str) + "\n"

        # Callback function to be passed down
        def progress_callback(stage, message, percent=None):
            # We can map internal stages to frontend stages if needed
            # For now, pass through
            # Calculate overall progress if percent is given for the sub-task
            overall_progress = None
            if percent is not None and total_docs > 0:
                doc_progress = percent / 100.0
                overall_progress = int(((current_doc_index + doc_progress) / total_docs) * 100)
            
            # We can't yield from here directly because this is a callback called by synchronous code.
            # But wait! We can't yield from a callback in a synchronous function.
            # This is the tricky part. 
            # Since `evaluate_answer` is synchronous, we can't stream OUT of it easily unless we use a queue or similar,
            # OR we just accept that we can't stream granular updates from within the sync function 
            # unless we change the architecture to be async or use a shared queue.
            
            # However, for a generator, we can't just "yield" from a nested function call.
            # The standard way in Python without async is to pass a queue or just log it.
            # But we want to stream it to the client.
            
            # Given the constraints and the synchronous nature of `evaluate_answer`, 
            # we might not be able to get granular updates *out* of the generator loop easily 
            # without refactoring `evaluate_answer` to be a generator itself.
            pass 

        # REFACTOR: To support streaming from deep within, we need `evaluate_answer` to yield or use a queue.
        # Since I cannot easily change `evaluate_answer` to a generator everywhere (it might break other callers),
        # I will use a queue-based approach or just accept stage-level updates for now.
        
        # BUT, since I am editing the code, I CAN change `evaluate_answer` to accept a callback 
        # that writes to a queue, and have a separate thread consume it? 
        # No, that's too complex for this context.
        
        # Alternative: Just yield stage updates from the top level loop, 
        # and maybe break down `evaluate_answer` in the loop if possible.
        # But `evaluate_answer` does a lot.
        
        # Let's try to make `evaluate_answer` a generator? 
        # If I change it to `yield`, I break the return value for other callers.
        
        # Let's stick to the plan: I added `progress_callback` to `evaluate_answer`.
        # But I can't use it to yield from the outer generator.
        # I can use a simple trick: The callback updates a shared state, but the generator is blocked!
        # The generator is blocked while `evaluate_answer` runs. So no yields will happen until it returns.
        
        # So, `evaluate_answer` MUST yield or be broken down.
        # I will create a new method `evaluate_answer_generator` that yields progress, 
        # and `evaluate_answer` can just consume it and return the final result.
        
        yield make_event("Starting evaluation process...", progress=0, stage="initializing")
        logger.info(f"Stream: Starting evaluation for session {session_id}")

        try:
            for resource_id in answer_resource_ids:
                
                # Find the answer document
                ad = self.answers.get_answer_document_by_session_and_resource(session_id, resource_id)
                if not ad:
                    yield make_event(f"Answer document for resource {resource_id} not found, skipping.", status="warning", stage="processing_documents")
                    continue

                try:
                    yield make_event(f"Evaluating answer document {current_doc_index + 1}/{total_docs}...", status="processing", stage="processing_documents")
                    logger.info(f"Stream: Evaluating answer document {ad.id}...")
                    
                    # Call the generator version of evaluate_answer
                    # I need to implement `evaluate_answer_generator`
                    for update in self.evaluate_answer_generator(ad.id, user_id):
                        # update is (stage, message, percent)
                        stage, msg, pct = update
                        
                        # Calculate overall progress
                        overall_progress = int(((current_doc_index + (pct/100.0 if pct else 0)) / total_docs) * 100)
                        yield make_event(msg, progress=overall_progress, stage=stage)
                    
                    current_doc_index += 1
                    yield make_event(f"Completed evaluation for document {current_doc_index}/{total_docs}", status="success", stage="completed")
                    logger.info(f"Stream: Evaluation finished for answer document {ad.id}.")
                    
                except Exception as e:
                    logger.error(f"Failed to evaluate answer {ad.id}: {e}")
                    yield make_event(f"Failed to evaluate document {current_doc_index + 1}: {str(e)}", status="error", stage="failed")
                    current_doc_index += 1
            
            self.sessions.update_evaluation_session(session_id, status="completed")
            yield make_event("Evaluation process completed successfully.", progress=100, status="completed", stage="completed")
            logger.info(f"Stream: Evaluation completed for session {session_id}")
            
        except Exception as e:
            logger.error(f"Critical error in evaluation stream: {e}")
            self.sessions.update_evaluation_session(session_id, status="failed")
            yield make_event(f"Evaluation process failed: {str(e)}", status="failed", stage="failed")

    def evaluate_answer_generator(self, answer_id: UUID, user_id: UUID):
        """
        Generator version of evaluate_answer.
        Yields (stage, message, percent) tuples.
        """
        # This duplicates logic from evaluate_answer but yields updates.
        # Ideally we refactor evaluate_answer to use this, but for safety I'll keep them separate or make evaluate_answer consume this.
        
        answer_doc = self._ensure_answer_owner(answer_id, user_id)
        
        yield ("processing_documents", "Checking answer resource...", 5)

        # Get the answer document with OCR text
        answer_resource = self.resource_files.get_resource(answer_doc.resource_id)
        if not answer_resource:
            raise ValueError("Answer resource not found")

        # OCR
        if not answer_resource.extracted_text:
            yield ("processing_documents", "Extracting text from answer script (OCR)...", 10)
            ocr_text, _ = extract_and_clean_text_from_file(answer_resource.storage_path)
            self.resource_files.update_resource_extracted_text(answer_resource.id, ocr_text)
        else:
            ocr_text = answer_resource.extracted_text
        
        yield ("processing_documents", "Loading evaluation context...", 20)
        
        # Context loading
        eval_session = self.sessions.get_evaluation_session(answer_doc.evaluation_session_id)
        if not eval_session: raise ValueError("Evaluation session not found")

        question_papers = self.question_papers.get_question_papers_by_chat_session(eval_session.session_id)
        if not question_papers: raise ValueError("Question paper not found")
        question_paper = question_papers[0]
        questions = self.question_papers.get_questions_by_paper(question_paper.id)

        # Fix OCR / Map
        if answer_doc.mapped_answers:
            yield ("processing_documents", "Using existing answer mapping...", 30)
            answer_mapping = answer_doc.mapped_answers
            if not answer_resource.extracted_text:
                 cleaned_answer_text = fix_sinhala_ocr(ocr_text)
            else:
                 cleaned_answer_text = answer_resource.extracted_text
        else:
            yield ("processing_documents", "Correcting OCR errors...", 30)
            cleaned_answer_text = fix_sinhala_ocr(ocr_text)
            
            yield ("processing_documents", "Mapping answers to questions...", 40)
            answer_mapping = map_student_answers(cleaned_answer_text, questions)
            self.answers.update_mapped_answers(answer_id, answer_mapping)
        
        # Grading
        yield ("evaluating_answers", "Starting grading process...", 50)
        
        from app.services.evaluation.grading_service import GradingService
        grader = GradingService(self.db)
        
        # We need to hook into grading service too. 
        # Since I added progress_callback to grade_answer_document, I can use it!
        
        def internal_callback(stage, msg, percent=None):
            # Map internal grading stages to our generator yields
            # Base progress for grading is 50% to 100%
            base = 50
            if percent:
                adjusted = base + (percent / 2) # Scale 0-100 to 50-100 range roughly
            else:
                adjusted = base
            
            # We can't yield from here directly (callback).
            # So we need a way to pass this out.
            # Since we are inside a generator `evaluate_answer_generator`, we can't yield from a callback.
            # This is the same problem.
            pass

        # Actually, I can't easily stream from `grader.grade_answer_document` unless I change IT to a generator too.
        # Or I use a queue.
        # Given the complexity, I will just yield major steps here and NOT use the callback for now, 
        # OR I will just accept that `grade_answer_document` is a black box that takes time.
        
        # BUT the user specifically asked for "steps on the backend terminal... to frontend".
        # The logs show "Grading question X...".
        
        # I will make `grade_answer_document` a generator? No, it returns a value.
        # I will use a queue to communicate from the callback to this generator.
        import queue
        q = queue.Queue()
        
        def queue_callback(stage, msg, percent=None):
            q.put((stage, msg, percent))
            
        import threading
        
        # Run grading in a separate thread so we can consume the queue in this generator
        result_container = {}
        error_container = {}
        
        def run_grading():
            try:
                result_container['result'] = grader.grade_answer_document(answer_id, user_id, queue_callback)
            except Exception as e:
                error_container['error'] = e
            finally:
                q.put(None) # Sentinel
        
        t = threading.Thread(target=run_grading)
        t.start()
        
        while True:
            item = q.get()
            if item is None:
                break
            stage, msg, percent = item
            # Scale progress: 50 + (percent/2)
            p = 50 + (percent / 2) if percent is not None else None
            yield (stage, msg, p)
            
        t.join()
        
        if 'error' in error_container:
            raise error_container['error']
            
        yield ("completed", "Evaluation completed.", 100)
        return result_container.get('result')

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

    def process_documents(self, chat_session_id: UUID, answer_resource_ids: List[UUID], user_id: UUID):
        from app.schemas.evaluation import DocumentProcessingStatus, ProcessDocumentsResponse
        from app.shared.models.session_resources import SessionResource
        
        results = []
        
        # 1. Process Syllabus
        try:
            syllabus_resource = self.db.query(SessionResource).filter(
                SessionResource.session_id == chat_session_id,
                SessionResource.label == "syllabus"
            ).first()
            
            if syllabus_resource:
                # Check if resource has extracted text
                resource = self.resource_files.get_resource(syllabus_resource.resource_id)
                if resource and resource.extracted_text:
                     results.append(DocumentProcessingStatus(
                        resource_id=syllabus_resource.resource_id,
                        role="syllabus",
                        status="already_processed",
                        message="Syllabus already processed."
                    ))
                elif resource:
                    # Process Syllabus
                    self.parse_syllabus(syllabus_resource.resource_id, user_id)
                    results.append(DocumentProcessingStatus(
                        resource_id=syllabus_resource.resource_id,
                        role="syllabus",
                        status="processed",
                        message="Syllabus processed successfully."
                    ))
                else:
                    results.append(DocumentProcessingStatus(
                        resource_id=syllabus_resource.resource_id,
                        role="syllabus",
                        status="failed",
                        message="Syllabus resource not found."
                    ))
            else:
                 results.append(DocumentProcessingStatus(
                        resource_id=chat_session_id,
                        role="syllabus",
                        status="failed",
                        message="No syllabus attached."
                    ))
        except Exception as e:
            logger.error(f"Error processing syllabus: {e}")
            results.append(DocumentProcessingStatus(
                resource_id=chat_session_id,
                role="syllabus",
                status="failed",
                message=str(e)
            ))

        # 2. Process Rubric (Marking Scheme)
        try:
            rubric_resource = self.db.query(SessionResource).filter(
                SessionResource.session_id == chat_session_id,
                SessionResource.label == "rubric"
            ).first()
            
            if rubric_resource:
                # Check if resource has extracted text
                resource = self.resource_files.get_resource(rubric_resource.resource_id)
                if resource and resource.extracted_text:
                     results.append(DocumentProcessingStatus(
                        resource_id=rubric_resource.resource_id,
                        role="rubric",
                        status="already_processed",
                        message="Rubric already processed."
                    ))
                elif resource:
                    # Process Rubric
                    self.parse_rubric(rubric_resource.resource_id, user_id)
                    results.append(DocumentProcessingStatus(
                        resource_id=rubric_resource.resource_id,
                        role="rubric",
                        status="processed",
                        message="Rubric processed successfully."
                    ))
                else:
                    results.append(DocumentProcessingStatus(
                        resource_id=rubric_resource.resource_id,
                        role="rubric",
                        status="failed",
                        message="Rubric resource not found."
                    ))
            else:
                # Check if a structured rubric is attached to the chat session
                chat_session = self.chat_sessions.get_session(chat_session_id)
                if chat_session and chat_session.rubric_id:
                     results.append(DocumentProcessingStatus(
                        resource_id=chat_session.rubric_id,
                        role="rubric",
                        status="already_processed",
                        message="Structured rubric attached."
                    ))
                else:
                     results.append(DocumentProcessingStatus(
                            resource_id=chat_session_id,
                            role="rubric",
                            status="failed",
                            message="No rubric attached."
                        ))
        except Exception as e:
            logger.error(f"Error processing rubric: {e}")
            results.append(DocumentProcessingStatus(
                resource_id=chat_session_id,
                role="rubric",
                status="failed",
                message=str(e)
            ))

        # 3. Process Question Paper
        try:
            # Check if QP is attached
            qp_resource = self.db.query(SessionResource).filter(
                SessionResource.session_id == chat_session_id,
                SessionResource.label == "question_paper"
            ).first()
            
            if qp_resource:
                # Check if already parsed
                existing_qp = self.question_papers.get_question_papers_by_chat_session(chat_session_id)
                if existing_qp:
                    results.append(DocumentProcessingStatus(
                        resource_id=qp_resource.resource_id,
                        role="question_paper",
                        status="already_processed",
                        message="Question paper already parsed."
                    ))
                else:
                    # Process QP
                    self.parse_question_paper(chat_session_id, user_id)
                    results.append(DocumentProcessingStatus(
                        resource_id=qp_resource.resource_id,
                        role="question_paper",
                        status="processed",
                        message="Question paper parsed successfully."
                    ))
            else:
                 results.append(DocumentProcessingStatus(
                        resource_id=chat_session_id, # Placeholder
                        role="question_paper",
                        status="failed",
                        message="No question paper attached."
                    ))

        except Exception as e:
            logger.error(f"Error processing question paper: {e}")
            results.append(DocumentProcessingStatus(
                resource_id=chat_session_id,
                role="question_paper",
                status="failed",
                message=str(e)
            ))

        # 4. Process Answer Scripts
        for res_id in answer_resource_ids:
            try:
                self._ensure_resource_owner(res_id, user_id)
                
                # Find existing session for this chat_session
                sessions = self.sessions.get_evaluation_sessions_by_chat_session(chat_session_id)
                session = sessions[0] if sessions else None
                
                if not session:
                    # Create a new session
                    payload = EvaluationSessionCreate(session_id=chat_session_id)
                    session = self.create_session(payload, user_id)
                
                # Check if AnswerDocument exists for this session and resource
                existing_ad = self.answers.get_answer_document_by_session_and_resource(session.id, res_id)
                
                if existing_ad and existing_ad.mapped_answers:
                     results.append(DocumentProcessingStatus(
                        resource_id=res_id,
                        role="answer_script",
                        status="already_processed",
                        message="Answer script already processed."
                    ))
                else:
                    # Process it
                    if not existing_ad:
                        existing_ad = self.answers.create_answer_document(
                            evaluation_session_id=session.id,
                            resource_id=res_id,
                            student_identifier=f"Student-{res_id}"
                        )
                    
                    # Run parsing logic
                    self.parse_answer_document(existing_ad.id, user_id)
                    
                    results.append(DocumentProcessingStatus(
                        resource_id=res_id,
                        role="answer_script",
                        status="processed",
                        message="Answer script processed successfully."
                    ))

            except Exception as e:
                logger.error(f"Error processing answer script {res_id}: {e}")
                results.append(DocumentProcessingStatus(
                    resource_id=res_id,
                    role="answer_script",
                    status="failed",
                    message=str(e)
                ))
                
        return ProcessDocumentsResponse(results=results)


    def process_documents_generator(self, chat_session_id: UUID, answer_resource_ids: List[UUID], user_id: UUID):
        """
        Generator that yields progress updates for document processing.
        Yields JSON strings formatted for SSE.
        """
        from app.schemas.evaluation import DocumentProcessingStatus
        from app.shared.models.session_resources import SessionResource
        import json

        total_steps = 3 + len(answer_resource_ids)
        current_step = 0
        
        def make_event(msg, status_obj=None):
            nonlocal current_step
            percent = int((current_step / total_steps) * 100)
            data = {
                "progress": percent,
                "message": msg,
                "detail": status_obj.dict() if status_obj else None
            }
            return json.dumps(data, default=str) + "\n"

        yield make_event("Starting document processing...")
        logger.info("Stream: Started processing")

        # 1. Process Syllabus
        try:
            syllabus_resource = self.db.query(SessionResource).filter(
                SessionResource.session_id == chat_session_id,
                SessionResource.label == "syllabus"
            ).first()
            
            status_obj = None
            if syllabus_resource:
                resource = self.resource_files.get_resource(syllabus_resource.resource_id)
                if resource and resource.extracted_text:
                     status_obj = DocumentProcessingStatus(
                        resource_id=syllabus_resource.resource_id,
                        role="syllabus",
                        status="already_processed",
                        message="Syllabus already processed."
                    )
                elif resource:
                    logger.info("Stream: Parsing Syllabus...")
                    self.parse_syllabus(syllabus_resource.resource_id, user_id)
                    status_obj = DocumentProcessingStatus(
                        resource_id=syllabus_resource.resource_id,
                        role="syllabus",
                        status="processed",
                        message="Syllabus processed successfully."
                    )
                else:
                    status_obj = DocumentProcessingStatus(
                        resource_id=syllabus_resource.resource_id,
                        role="syllabus",
                        status="failed",
                        message="Syllabus resource not found."
                    )
            else:
                 status_obj = DocumentProcessingStatus(
                        resource_id=chat_session_id,
                        role="syllabus",
                        status="failed",
                        message="No syllabus attached."
                    )
            
            current_step += 1
            logger.info("Stream: Syllabus complete")
            yield make_event("Syllabus check complete", status_obj)
            
        except Exception as e:
            logger.error(f"Error processing syllabus: {e}")
            current_step += 1
            yield make_event(f"Syllabus failed: {e}", DocumentProcessingStatus(
                resource_id=chat_session_id,
                role="syllabus",
                status="failed",
                message=str(e)
            ))

        # 2. Process Rubric
        try:
            rubric_resource = self.db.query(SessionResource).filter(
                SessionResource.session_id == chat_session_id,
                SessionResource.label == "rubric"
            ).first()
            
            status_obj = None
            if rubric_resource:
                resource = self.resource_files.get_resource(rubric_resource.resource_id)
                if resource and resource.extracted_text:
                     status_obj = DocumentProcessingStatus(
                        resource_id=rubric_resource.resource_id,
                        role="rubric",
                        status="already_processed",
                        message="Rubric already processed."
                    )
                elif resource:
                    logger.info("Stream: Parsing Rubric...")
                    self.parse_rubric(rubric_resource.resource_id, user_id)
                    status_obj = DocumentProcessingStatus(
                        resource_id=rubric_resource.resource_id,
                        role="rubric",
                        status="processed",
                        message="Rubric processed successfully."
                    )
                else:
                    status_obj = DocumentProcessingStatus(
                        resource_id=rubric_resource.resource_id,
                        role="rubric",
                        status="failed",
                        message="Rubric resource not found."
                    )
            else:
                chat_session = self.chat_sessions.get_session(chat_session_id)
                if chat_session and chat_session.rubric_id:
                     status_obj = DocumentProcessingStatus(
                        resource_id=chat_session.rubric_id,
                        role="rubric",
                        status="already_processed",
                        message="Structured rubric attached."
                    )
                else:
                     status_obj = DocumentProcessingStatus(
                            resource_id=chat_session_id,
                            role="rubric",
                            status="failed",
                            message="No rubric attached."
                        )
            
            current_step += 1
            logger.info("Stream: Rubric complete")
            yield make_event("Rubric check complete", status_obj)

        except Exception as e:
            logger.error(f"Error processing rubric: {e}")
            current_step += 1
            yield make_event(f"Rubric failed: {e}", DocumentProcessingStatus(
                resource_id=chat_session_id,
                role="rubric",
                status="failed",
                message=str(e)
            ))

        # 3. Process Question Paper
        try:
            qp_resource = self.db.query(SessionResource).filter(
                SessionResource.session_id == chat_session_id,
                SessionResource.label == "question_paper"
            ).first()
            
            status_obj = None
            if qp_resource:
                existing_qp = self.question_papers.get_question_papers_by_chat_session(chat_session_id)
                if existing_qp:
                    status_obj = DocumentProcessingStatus(
                        resource_id=qp_resource.resource_id,
                        role="question_paper",
                        status="already_processed",
                        message="Question paper already parsed."
                    )
                else:
                    logger.info("Stream: Parsing Question Paper...")
                    self.parse_question_paper(chat_session_id, user_id)
                    status_obj = DocumentProcessingStatus(
                        resource_id=qp_resource.resource_id,
                        role="question_paper",
                        status="processed",
                        message="Question paper parsed successfully."
                    )
            else:
                 status_obj = DocumentProcessingStatus(
                        resource_id=chat_session_id,
                        role="question_paper",
                        status="failed",
                        message="No question paper attached."
                    )
            
            current_step += 1
            logger.info("Stream: Question Paper complete")
            yield make_event("Question paper check complete", status_obj)

        except Exception as e:
            logger.error(f"Error processing question paper: {e}")
            current_step += 1
            yield make_event(f"Question paper failed: {e}", DocumentProcessingStatus(
                resource_id=chat_session_id,
                role="question_paper",
                status="failed",
                message=str(e)
            ))

        # 4. Process Answer Scripts
        for res_id in answer_resource_ids:
            try:
                self._ensure_resource_owner(res_id, user_id)
                
                sessions = self.sessions.get_evaluation_sessions_by_chat_session(chat_session_id)
                session = sessions[0] if sessions else None
                
                if not session:
                    from app.schemas.evaluation import EvaluationSessionCreate
                    payload = EvaluationSessionCreate(session_id=chat_session_id)
                    session = self.create_session(payload, user_id)
                
                existing_ad = self.answers.get_answer_document_by_session_and_resource(session.id, res_id)
                
                status_obj = None
                if existing_ad and existing_ad.mapped_answers:
                     status_obj = DocumentProcessingStatus(
                        resource_id=res_id,
                        role="answer_script",
                        status="already_processed",
                        message="Answer script already processed."
                    )
                else:
                    if not existing_ad:
                        existing_ad = self.answers.create_answer_document(
                            evaluation_session_id=session.id,
                            resource_id=res_id,
                            student_identifier=f"Student-{res_id}"
                        )
                    
                    logger.info(f"Stream: Parsing Answer Script {res_id}...")
                    self.parse_answer_document(existing_ad.id, user_id)
                    
                    status_obj = DocumentProcessingStatus(
                        resource_id=res_id,
                        role="answer_script",
                        status="processed",
                        message="Answer script processed successfully."
                    )
                
                current_step += 1
                logger.info(f"Stream: Answer Script {res_id} complete")
                yield make_event(f"Answer script {res_id} processed", status_obj)

            except Exception as e:
                logger.error(f"Error processing answer script {res_id}: {e}")
                current_step += 1
                yield make_event(f"Answer script failed: {e}", DocumentProcessingStatus(
                    resource_id=res_id,
                    role="answer_script",
                    status="failed",
                    message=str(e)
                ))
        
        # Final Event
        logger.info("Stream: All complete")
        yield json.dumps({"progress": 100, "message": "All documents processed", "status": "completed"}) + "\n"

    def parse_syllabus(self, resource_id: UUID, user_id: UUID):
        """
        Parse syllabus by extracting text and cleaning it with AI.
        """
        self._ensure_resource_owner(resource_id, user_id)
        resource = self.resource_files.get_resource(resource_id)
        
        if not resource.storage_path:
             raise ValueError("Resource file not found on disk")

        logger.info(f"Parsing syllabus: {resource_id}")

        # OCR
        cleaned_text, _ = extract_and_clean_text_from_file(resource.storage_path)
        logger.info(f"OCR complete for syllabus. Length: {len(cleaned_text)}")
        
        # AI Fix
        cleaned_text = fix_sinhala_ocr(cleaned_text)
        logger.info(f"AI correction complete for syllabus. Length: {len(cleaned_text)}")
        
        # Save
        resource.extracted_text = cleaned_text
        self.resource_files.db.commit()

    def parse_rubric(self, resource_id: UUID, user_id: UUID):
        """
        Parse rubric (marking scheme) by extracting text and cleaning it with AI.
        """
        self._ensure_resource_owner(resource_id, user_id)
        resource = self.resource_files.get_resource(resource_id)
        
        if not resource.storage_path:
             raise ValueError("Resource file not found on disk")

        logger.info(f"Parsing rubric: {resource_id}")

        # OCR
        cleaned_text, _ = extract_and_clean_text_from_file(resource.storage_path)
        logger.info(f"OCR complete for rubric. Length: {len(cleaned_text)}")
        
        # AI Fix
        cleaned_text = fix_sinhala_ocr(cleaned_text)
        logger.info(f"AI correction complete for rubric. Length: {len(cleaned_text)}")
        
        # Save
        resource.extracted_text = cleaned_text
        self.resource_files.db.commit()


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

            # Fix Sinhala OCR errors using AI
            logger.info("Running AI correction on extracted text...")
            cleaned_text = fix_sinhala_ocr(cleaned_text)
            logger.info("AI correction complete. Final text length: %s", len(cleaned_text))

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
                    total_marks=config.get("total_marks"),
                    weightage=float(config.get("suggested_weightage")) if config.get("suggested_weightage") is not None else None,
                    total_main_questions=config.get("total_questions_available"),
                    selection_rules=config.get("selection_rules"),
                )

                # 2️⃣ Create Questions
                questions_dict = paper_data.get("questions", {}) or {}
                for q_num, q_data in questions_dict.items():
                    normalized_q_num = self._normalize_question_number(q_num)
                    question = self.question_papers.create_question(
                        question_paper_id=question_paper.id,
                        question_number=normalized_q_num,
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
                            normalized_label = self._normalize_sub_question_label(label)
                            sq = self.question_papers.create_sub_question(
                                question_id=parent_q_id,
                                label=normalized_label,
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
        chat_session_id = self._resolve_session_id(session_id)
        self._ensure_chat_session_owner(chat_session_id, user_id)
        question_papers = self.question_papers.get_question_papers_by_chat_session(chat_session_id)
        if not question_papers:
            return []

        return self.question_papers.get_questions_by_paper(question_papers[0].id)

    def save_paper_config(self, session_id: UUID, payload: List[PaperConfigCreate], user_id: UUID):
        self._ensure_chat_session_owner(session_id, user_id)
        saved_configs = []
        for config in payload:
            saved = self.paper_configs.save_config(
                chat_session_id=session_id,
                paper_part=config.paper_part,
                subject_name=config.subject_name,
                medium=config.medium,
                total_marks=config.total_marks,
                weightage=float(config.weightage) if config.weightage is not None else None,
                total_main_questions=config.total_main_questions,
                selection_rules=config.selection_rules,
                is_confirmed=config.is_confirmed,
            )
            saved_configs.append(saved)
        return saved_configs

    def get_paper_config(self, session_id: UUID, user_id: UUID):
        self._ensure_chat_session_owner(session_id, user_id)
        return self.paper_configs.get_config(chat_session_id=session_id)

    def confirm_paper_config(self, session_id: UUID, payload: Union[PaperConfigUpdate, List[PaperConfigUpdate]], user_id: UUID):
        """Update provided fields and confirm the paper configuration for an evaluation session."""
        self._ensure_chat_session_owner(session_id, user_id)
        
        configs = []
        
        if isinstance(payload, list):
            # Handle list of updates
            for update in payload:
                result = self.paper_configs.confirm_config(
                    chat_session_id=session_id,
                    paper_part=update.paper_part,
                    subject_name=update.subject_name,
                    medium=update.medium,
                    total_marks=update.total_marks,
                    weightage=float(update.weightage) if update.weightage is not None else None,
                    total_main_questions=update.total_main_questions,
                    selection_rules=update.selection_rules,
                )
                if isinstance(result, list):
                    configs.extend(result)
                elif result:
                    configs.append(result)
        else:
            # Handle single update
            result = self.paper_configs.confirm_config(
                chat_session_id=session_id,
                paper_part=payload.paper_part,
                subject_name=payload.subject_name,
                medium=payload.medium,
                total_marks=payload.total_marks,
                weightage=float(payload.weightage) if payload.weightage is not None else None,
                total_main_questions=payload.total_main_questions,
                selection_rules=payload.selection_rules,
            )
            if isinstance(result, list):
                configs.extend(result)
            elif result:
                configs.append(result)
        
        # Update Global Context with this new configuration
        from app.services.evaluation.user_context_service import UserContextService
        context_service = UserContextService(self.db)
        
        config_data = []
        for config in configs:
            config_data.append({
                "paper_part": config.paper_part,
                "subject_name": config.subject_name,
                "medium": config.medium,
                "total_marks": config.total_marks,
                "weightage": float(config.weightage) if config.weightage else None,
                "total_main_questions": config.total_main_questions,
                "selection_rules": config.selection_rules
            })
            
        context_service.update_paper_config(user_id, config_data)
        
        return configs

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

    def parse_answer_document(self, answer_id: UUID, user_id: UUID):
        """
        Parse and map student answers to questions without evaluating.
        Returns the mapping for verification.
        """
        answer_doc = self._ensure_answer_owner(answer_id, user_id)

        # Check if already mapped
        if answer_doc.mapped_answers:
            return {
                "answer_document_id": answer_id,
                "extracted_text": None,
                "mapped_answers": answer_doc.mapped_answers
            }

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

        question_paper = question_papers[0]
        questions = self.question_papers.get_questions_by_paper(question_paper.id)

        # 1. Fix OCR errors
        cleaned_answer_text = fix_sinhala_ocr(ocr_text)
        
        # 2. Map answers
        answer_mapping = map_student_answers(cleaned_answer_text, questions)
        
        # Save mapped answers
        self.answers.update_mapped_answers(answer_id, answer_mapping)
        
        return {
            "answer_document_id": answer_id,
            "extracted_text": cleaned_answer_text,
            "mapped_answers": answer_mapping
        }

    def get_answer_mapping(self, answer_id: UUID, user_id: UUID):
        """Get the stored mapping for an answer document."""
        answer_doc = self._ensure_answer_owner(answer_id, user_id)
        
        # Get resource for text
        resource = self.resource_files.get_resource(answer_doc.resource_id)
        
        return {
            "answer_document_id": answer_id,
            "mapped_answers": answer_doc.mapped_answers,
            "extracted_text": resource.extracted_text if resource else None
        }

    def get_syllabus_content(self, session_id: UUID, user_id: UUID):
        """Get the extracted text of the syllabus attached to the session."""
        chat_session_id = self._resolve_session_id(session_id)
        self._ensure_chat_session_owner(chat_session_id, user_id)
        
        from app.shared.models.session_resources import SessionResource
        syllabus_resource = self.db.query(SessionResource).filter(
            SessionResource.session_id == chat_session_id,
            SessionResource.label == "syllabus"
        ).first()
        
        if not syllabus_resource:
            raise ValueError("No syllabus attached to this session")
            
        resource = self.resource_files.get_resource(syllabus_resource.resource_id)
        if not resource:
            raise ValueError("Syllabus resource file not found")
            
        return {
            "resource_id": resource.id,
            "extracted_text": resource.extracted_text
        }

    def get_rubric_content(self, session_id: UUID, user_id: UUID):
        """Get the extracted text of the rubric attached to the session."""
        chat_session_id = self._resolve_session_id(session_id)
        self._ensure_chat_session_owner(chat_session_id, user_id)
        
        from app.shared.models.session_resources import SessionResource
        rubric_resource = self.db.query(SessionResource).filter(
            SessionResource.session_id == chat_session_id,
            SessionResource.label == "rubric"
        ).first()
        
        if not rubric_resource:
            raise ValueError("No rubric attached to this session")
            
        resource = self.resource_files.get_resource(rubric_resource.resource_id)
        if not resource:
            raise ValueError("Rubric resource file not found")
            
        return {
            "resource_id": resource.id,
            "extracted_text": resource.extracted_text
        }

    def evaluate_answer(self, answer_id: UUID, user_id: UUID, progress_callback=None):
        """Evaluate answer with recursive sub-question support."""
        answer_doc = self._ensure_answer_owner(answer_id, user_id)

        # Check if already evaluated - FORCE RE-EVALUATION if requested or just proceed
        # For debugging purposes, we might want to allow re-evaluation.
        # But standard flow checks existence.
        # existing = self.answers.get_evaluation_result_by_answer_document(answer_id)
        # if existing:
        #    return existing
        
        # If existing result exists, we will handle it in GradingService (update instead of delete)
        # This avoids potential FK issues with delete/create cycles in the same flow.

        if progress_callback:
            progress_callback("processing_documents", "Checking answer resource...")

        # Get the answer document with OCR text
        answer_resource = self.resource_files.get_resource(answer_doc.resource_id)
        if not answer_resource:
            raise ValueError("Answer resource not found")

        # OCR the answer script if not already done
        if not answer_resource.extracted_text:
            if progress_callback:
                progress_callback("processing_documents", "Extracting text from answer script (OCR)...")
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
        
        # Get full question objects for the prompt
        questions = self.question_papers.get_questions_by_paper(question_paper.id)

        # 1. Fix OCR errors in student answer
        if answer_doc.mapped_answers:
            logger.info("Using existing answer mapping...")
            answer_mapping = answer_doc.mapped_answers
            # We still need the text for the prompt if we were doing grading, 
            # but if we have mapping, we might assume text is extracted.
            # For now, let's just ensure we have text.
            if not answer_resource.extracted_text:
                 cleaned_answer_text = fix_sinhala_ocr(ocr_text)
            else:
                 cleaned_answer_text = answer_resource.extracted_text
        else:
            if progress_callback:
                progress_callback("processing_documents", "Correcting OCR errors...")
            logger.info("Running AI correction on student answer script...")
            cleaned_answer_text = fix_sinhala_ocr(ocr_text)
            
            # 2. Map answers to questions using AI
            if progress_callback:
                progress_callback("processing_documents", "Mapping answers to questions...")
            logger.info("Mapping student answers to questions...")
            answer_mapping = map_student_answers(cleaned_answer_text, questions)
            
            # Save mapping for future use
            self.answers.update_mapped_answers(answer_id, answer_mapping)
        
        # Log the mapping for debugging
        logger.info(f"Mapped {len(answer_mapping)} answers.")
        logger.debug(f"Answer Mapping: {answer_mapping}")

        # 3. Perform Grading
        if progress_callback:
            progress_callback("evaluating_answers", "Starting grading process...")
        logger.info("Starting grading process...")
        from app.services.evaluation.grading_service import GradingService
        grader = GradingService(self.db)
        result = grader.grade_answer_document(answer_id, user_id, progress_callback)
        logger.info(f"Grading completed for answer document {answer_id}.")
        return result


    def get_evaluation_result(self, answer_id: UUID, user_id: UUID):
        self._ensure_answer_owner(answer_id, user_id)
        result = self.answers.get_evaluation_result_by_answer_document(answer_id)
        if not result:
            return None
        return self.answers.get_complete_evaluation_result(result.id)

    def get_answer_mapping_details(self, answer_id: UUID, user_id: UUID):
        """
        Get detailed answer mapping with question text and numbering.
        """
        mapping_data = self.get_answer_mapping(answer_id, user_id)
        mapped_answers = mapping_data.get("mapped_answers", {}) or {}
        
        # Get Question Paper
        answer_doc = self.answers.get_answer_document(answer_id)
        eval_session = self.sessions.get_evaluation_session(answer_doc.evaluation_session_id)
        question_papers = self.question_papers.get_question_papers_by_chat_session(eval_session.session_id)
        
        if not question_papers:
            return {"details": [], "raw_mapping": mapped_answers}
            
        question_paper = question_papers[0]
        questions = self.question_papers.get_questions_by_paper(question_paper.id)
        
        # Build Lookup
        lookup = {}
        for q in questions:
            lookup[str(q.id)] = {
                "type": "question",
                "number": q.question_number,
                "text": q.question_text,
                "marks": q.max_marks
            }
            # Recursively add subquestions
            def add_subs(subs, parent_num):
                for sq in subs:
                    full_num = f"{parent_num}({sq.label})" if parent_num else sq.label
                    lookup[str(sq.id)] = {
                        "type": "sub_question",
                        "number": full_num,
                        "label": sq.label,
                        "text": sq.sub_question_text,
                        "marks": sq.max_marks,
                        "parent_id": str(q.id)
                    }
                    if sq.children:
                        add_subs(sq.children, full_num)
            
            add_subs(q.sub_questions, q.question_number)

        # Combine
        details = []
        for q_uuid, answer_text in mapped_answers.items():
            q_info = lookup.get(q_uuid, {"number": "Unknown", "text": "Unknown Question"})
            details.append({
                "question_id": q_uuid,
                "question_number": q_info.get("number"),
                "question_text": q_info.get("text"),
                "student_answer": answer_text,
                "max_marks": q_info.get("marks")
            })
            
        # Sort by question number (simple sort)
        def natural_sort_key(item):
            import re
            text = item["question_number"] or ""
            return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', text)]

        details.sort(key=natural_sort_key)
        
        return details

