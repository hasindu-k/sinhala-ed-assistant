from typing import Optional, List, Dict
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.message_repository import MessageRepository
from app.shared.models.message import Message


class MessageService:
    """Business logic for chat messages."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = MessageRepository(db)

    def validate_message_payload(self, modality: str, content: Optional[str], audio_url: Optional[str]):
        """Validate message creation payload."""
        if modality not in ["text", "voice", "image", "file"]:
            raise ValueError(f"Invalid modality: {modality}")
        
        if modality == "text" and not content:
            raise ValueError("Text messages must have content")
        
        if modality == "voice" and not audio_url:
            raise ValueError("Voice messages must have audio_url")

    def create_user_message_with_validation(
        self,
        session_id: UUID,
        user_id: UUID,
        content: Optional[str],
        modality: str = "text",
        grade_level: Optional[str] = None,
        audio_url: Optional[str] = None,
        transcript: Optional[str] = None,
        audio_duration_sec: Optional[float] = None,
        session_service = None,
    ):
        """Create user message with session ownership validation."""
        # Import here to avoid circular dependency
        if session_service is None:
            from app.services.chat_session_service import ChatSessionService
            session_service = ChatSessionService(self.db)
        
        # Validate session and ownership
        session_service.get_session_with_ownership_check(session_id, user_id)
        
        # Validate message payload
        self.validate_message_payload(modality, content, audio_url)
        
        # Create message
        return self.repository.create_user_message(
            session_id=session_id,
            content=content,
            modality=modality,
            grade_level=grade_level,
            audio_url=audio_url,
            transcript=transcript,
            audio_duration_sec=audio_duration_sec,
        )

    def create_user_message(
        self,
        session_id: UUID,
        content: Optional[str],
        modality: str = "text",
        grade_level: Optional[str] = None,
        audio_url: Optional[str] = None,
        transcript: Optional[str] = None,
        audio_duration_sec: Optional[float] = None,
    ):
        return self.repository.create_user_message(
            session_id=session_id,
            content=content,
            modality=modality,
            grade_level=grade_level,
            audio_url=audio_url,
            transcript=transcript,
            audio_duration_sec=audio_duration_sec,
        )

    def create_system_message(self, session_id: UUID, content: Optional[str]):
        return self.repository.create_system_message(session_id, content)

    def create_assistant_message(
        self,
        session_id: UUID,
        content: Optional[str],
        model_info: Optional[Dict] = None,
    ):
        return self.repository.create_assistant_message(
            session_id=session_id,
            content=content,
            model_info=model_info,
        )

    def list_session_messages(self, session_id: UUID) -> List:
        return self.repository.list_session_messages(session_id)
    
    def get_message(self, message_id: UUID) -> Optional[Message]:
        """Get a single message by ID."""
        return self.db.query(Message).filter(Message.id == message_id).first()
    
    def get_message_with_ownership_check(self, message_id: UUID, user_id: UUID, session_service=None):
        """Get message and validate session ownership."""
        message = self.get_message(message_id)
        if not message:
            raise ValueError("Message not found")
        
        # Import here to avoid circular dependency
        if session_service is None:
            from app.services.chat_session_service import ChatSessionService
            session_service = ChatSessionService(self.db)
        
        # Validate session ownership
        if not session_service.validate_ownership(message.session_id, user_id):
            raise PermissionError("You don't have permission to access this message")
        
        return message
    
    def get_message_details(self, message_id: UUID, user_id: UUID):
        """Get message with all related details."""
        message = self.get_message_with_ownership_check(message_id, user_id)
        
        # Get additional details
        # TODO: consolidate these service calls into a single repo join to reduce round trips
        from app.services.message_attachment_service import MessageAttachmentService
        from app.services.message_context_service import MessageContextService
        from app.services.message_safety_service import MessageSafetyService
        
        attachment_service = MessageAttachmentService(self.db)
        context_service = MessageContextService(self.db)
        safety_service = MessageSafetyService(self.db)
        
        attachments = attachment_service.get_message_resources(message_id)
        sources = context_service.get_message_sources(message_id)
        safety_report = safety_service.get_safety_report(message_id)
        
        return {
            **message.__dict__,
            "attachments": attachments,
            "sources": sources,
            "safety_report": safety_report,
        }
    
    def delete_message(self, message_id: UUID, user_id: UUID):
        """Delete message after ownership validation."""
        message = self.get_message_with_ownership_check(message_id, user_id)
        
        self.db.delete(message)
        self.db.commit()
    
    def attach_resources_to_message(
        self,
        message_id: UUID,
        user_id: UUID,
        resource_ids: List[UUID],
        display_name: Optional[str] = None,
        attachment_type: Optional[str] = None,
    ):
        """Attach resources to message after validation."""
        if not resource_ids:
            raise ValueError("At least one resource ID is required")
        
        # Validate message and ownership
        self.get_message_with_ownership_check(message_id, user_id)

        # Validate resources (exist + ownership)
        from app.services.resource_service import ResourceService
        resource_service = ResourceService(self.db)
        resource_service.ensure_resources_owned(resource_ids, user_id)

        # Attach resources
        from app.services.message_attachment_service import MessageAttachmentService
        attachment_service = MessageAttachmentService(self.db)
        
        attachments = []
        for resource_id in resource_ids:
            attachment = attachment_service.attach_resource(
                message_id=message_id,
                resource_id=resource_id,
                display_name=display_name,
                attachment_type=attachment_type,
            )
            attachments.append(attachment)
        
        return attachments
    
    def detach_resources_from_message(
        self,
        message_id: UUID,
        user_id: UUID,
        resource_ids: List[UUID],
    ):
        """Detach resources from message after validation."""
        if not resource_ids:
            raise ValueError("At least one resource ID is required")
        
        # Validate message and ownership
        self.get_message_with_ownership_check(message_id, user_id)

        # Detach resources
        from app.services.message_attachment_service import MessageAttachmentService
        attachment_service = MessageAttachmentService(self.db)
        
        for resource_id in resource_ids:
            attachment_service.detach_resource(
                message_id=message_id,
                resource_id=resource_id,
            )
            
    def generate_ai_response(
        self,
        message_id: UUID,
        user_id: UUID,
        resource_ids: Optional[List[UUID]] = None,
    ):
        """Generate AI response for a user message."""
        message = self.get_message_with_ownership_check(message_id, user_id)
        
        if message.role != "user":
            raise ValueError("Can only generate responses for user messages")
        
        user_query = message.content or message.transcript or ""
        if not user_query:
            raise ValueError("Cannot generate response without user query content")
        
        # Generate response using RAG
        # TODO: inject RAG service to reuse LLM client/config rather than instantiating each call
        from app.services.rag_service import RAGService
        rag_service = RAGService(self.db)
        
        result = rag_service.generate_response(
            session_id=message.session_id,
            user_message_id=message_id,
            user_query=user_query,
            resource_ids=resource_ids or [],
        )
        
        # Get the created assistant message
        assistant_message = self.db.query(Message).filter(
            Message.id == result["assistant_message_id"]
        ).first()
        
        return assistant_message
