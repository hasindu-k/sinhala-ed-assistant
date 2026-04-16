from app.services.chat_session_service import ChatSessionService
from app.services.message_service import MessageService
from app.services.message_attachment_service import MessageAttachmentService
from app.services.message_context_service import MessageContextService
from app.services.message_safety_service import MessageSafetyService
from app.services.resource_service import ResourceService
from app.services.resource_chunk_service import ResourceChunkService
from app.services.session_resource_service import SessionResourceService
from app.services.user_service import UserService

__all__ = [
    "ChatSessionService",
    "MessageService",
    "MessageAttachmentService",
    "MessageContextService",
    "MessageSafetyService",
    "ResourceService",
    "ResourceChunkService",
    "SessionResourceService",
    "UserService",
    "RubricService",
    "QuestionPaperService",
    "AnswerEvaluationService",
    "EvaluationSessionService",
    "EvaluationResourceService",
    "PaperConfigService",
    "EvaluationWorkflowService",
]


def __getattr__(name):
    if name in {
        "RubricService",
        "QuestionPaperService",
        "AnswerEvaluationService",
        "EvaluationSessionService",
        "EvaluationResourceService",
        "PaperConfigService",
        "EvaluationWorkflowService",
    }:
        from app.services import evaluation as evaluation_services

        return getattr(evaluation_services, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
