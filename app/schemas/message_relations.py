from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID
from decimal import Decimal


class MessageContextChunkCreate(BaseModel):
    message_id: UUID
    chunk_id: UUID
    similarity_score: Optional[Decimal] = None
    rank: Optional[int] = None


class MessageContextChunkResponse(BaseModel):
    id: int
    message_id: UUID
    chunk_id: UUID
    similarity_score: Optional[Decimal]
    rank: Optional[int]

    class Config:
        from_attributes = True


class MessageAttachmentCreate(BaseModel):
    message_id: UUID
    resource_id: UUID
    display_name: Optional[str] = None
    attachment_type: Optional[str] = None


class MessageAttachmentResponse(BaseModel):
    id: UUID
    message_id: UUID
    resource_id: UUID
    display_name: Optional[str]
    attachment_type: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class MessageSafetyReportCreate(BaseModel):
    message_id: UUID
    missing_concepts: Optional[dict] = None
    extra_concepts: Optional[dict] = None
    flagged_sentences: Optional[dict] = None
    reasoning: Optional[dict] = None


class MessageSafetyReportResponse(BaseModel):
    id: UUID
    message_id: UUID
    missing_concepts: Optional[str]
    extra_concepts: Optional[str]
    flagged_sentences: Optional[str]
    reasoning: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
