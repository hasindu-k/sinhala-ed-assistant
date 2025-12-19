# app/services/__init__.py

# Export core service classes for convenient imports across the app

from app.services.chat_session_service import ChatSessionService
from app.services.message_service import MessageService
from app.services.message_attachment_service import MessageAttachmentService
from app.services.message_context_service import MessageContextService
from app.services.message_safety_service import MessageSafetyService
from app.services.resource_service import ResourceService
from app.services.resource_chunk_service import ResourceChunkService
from app.services.session_resource_service import SessionResourceService
from app.services.user_service import UserService

# Evaluation domain services (already follow Service + Repository)
from app.services.evaluation import (
    RubricService,
    QuestionPaperService,
    AnswerEvaluationService,
    EvaluationSessionService,
)

__all__ = [
    # core services
    "ChatSessionService",
    "MessageService",
    "MessageAttachmentService",
    "MessageContextService",
    "MessageSafetyService",
    "ResourceService",
    "ResourceChunkService",
    "SessionResourceService",
    "UserService",
    # evaluation services
    "RubricService",
    "QuestionPaperService",
    "AnswerEvaluationService",
    "EvaluationSessionService",
]
