from pydantic import BaseModel
from typing import Optional, Any, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from enum import Enum


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class MessageModality(str, Enum):
    text = "text"
    voice = "voice"


class GradeLevel(str, Enum):
    grade_6_8 = "grade_6_8"
    grade_9_11 = "grade_9_11"
    grade_12_13 = "grade_12_13"
    university = "university"

class MessageAttachmentType(str, Enum):
    audio = "audio"
    image = "image"
    file = "file"
    document = "document"


# Message Schemas
class MessageAttachment(BaseModel):
    resource_id: UUID
    display_name: Optional[str] = None
    attachment_type: Optional[str] = "pdf"

class MessageCreate(BaseModel):
    content: str
    role: str = "user"
    modality: MessageModality = MessageModality.text
    audio_url: Optional[str] = None
    transcript: Optional[str] = None
    audio_duration_sec: Optional[Decimal] = None
    grade_level: Optional[str] = None  


class MessageUpdate(BaseModel):
    content: Optional[str] = None
    transcript: Optional[str] = None
    audio_duration_sec: Optional[Decimal] = None
    grade_level: Optional[GradeLevel] = None
    attachments: Optional[List[MessageAttachment]] = None


class MessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    role: MessageRole
    modality: MessageModality
    content: Optional[str] = None
    grade_level: Optional[GradeLevel] = None
    audio_url: Optional[str] = None
    transcript: Optional[str] = None
    audio_duration_sec: Optional[Decimal] = None
    created_at: datetime
    resource_ids: list[UUID] = []

    class Config:
        from_attributes = True

class MessageCreateResponse(BaseModel):
    id: UUID
    session_id: UUID
    role: MessageRole
    modality: MessageModality
    content: Optional[str] = None
    grade_level: Optional[GradeLevel] = None
    audio_url: Optional[str] = None
    transcript: Optional[str] = None
    audio_duration_sec: Optional[Decimal] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Message Attachment Schemas
class MessageAttachmentCreate(BaseModel):
    resource_id: UUID
    display_name: Optional[str] = None
    attachment_type: Optional[str] = None


class MessageAttachmentResponse(BaseModel):
    id: UUID
    message_id: UUID
    resource_id: UUID
    display_name: Optional[str] = None
    attachment_type: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MessageAttachmentWithResource(BaseModel):
    id: UUID
    message_id: UUID
    resource_id: UUID
    display_name: Optional[str] = None
    attachment_type: Optional[str] = None
    created_at: datetime
    # Resource details
    resource_filename: Optional[str] = None
    resource_mime_type: Optional[str] = None
    resource_size_bytes: Optional[int] = None
    resource_storage_path: Optional[str] = None

    class Config:
        from_attributes = True


class MessageWithAttachmentsResponse(BaseModel):
    id: UUID
    session_id: UUID
    role: MessageRole
    modality: MessageModality
    content: Optional[str] = None
    grade_level: Optional[GradeLevel] = None
    audio_url: Optional[str] = None
    transcript: Optional[str] = None
    audio_duration_sec: Optional[Decimal] = None
    created_at: datetime
    attachments: List[MessageAttachmentWithResource] = []

    class Config:
        from_attributes = True


class MessageAttachRequest(BaseModel):
    resource_ids: list[UUID]
    display_name: Optional[str] = None
    attachment_type: Optional[MessageAttachmentType] = None

class MessageDetachRequest(BaseModel):
    resource_ids: list[UUID]


# Message Context Schemas
class MessageContextChunkResponse(BaseModel):
    id: int
    message_id: UUID
    chunk_id: UUID
    similarity_score: Optional[Decimal] = None
    rank: Optional[int] = None

    class Config:
        from_attributes = True


# Message Safety Report Schemas
class MessageSafetyReportCreate(BaseModel):
    missing_concepts: Optional[Any] = None
    extra_concepts: Optional[Any] = None
    flagged_sentences: Optional[Any] = None
    reasoning: Optional[Any] = None


class MessageSafetyReportResponse(BaseModel):
    id: UUID
    message_id: UUID
    missing_concepts: Optional[str] = None
    extra_concepts: Optional[str] = None
    flagged_sentences: Optional[str] = None
    reasoning: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Combined Message Response with Relations
class MessageDetail(BaseModel):
    id: UUID
    session_id: UUID
    role: MessageRole
    modality: MessageModality
    content: Optional[str] = None
    grade_level: Optional[GradeLevel] = None
    audio_url: Optional[str] = None
    transcript: Optional[str] = None
    audio_duration_sec: Optional[Decimal] = None
    model_name: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    created_at: datetime
    attachments: list[MessageAttachmentResponse] = []
    context_chunks: list[MessageContextChunkResponse] = []
    safety_report: Optional[MessageSafetyReportResponse] = None

    class Config:
        from_attributes = True


# AI Response Generation Request
class GenerateResponseRequest(BaseModel):
    use_rag: bool = True
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
