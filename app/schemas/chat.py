from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime
from enum import Enum


class ChatMode(str, Enum):
    learning = "learning"
    evaluation = "evaluation"


class ChatChannel(str, Enum):
    text = "text"
    voice = "voice"
    mixed = "mixed"


class ChatSessionCreate(BaseModel):
    mode: ChatMode = Field(default=ChatMode.learning)
    channel: ChatChannel = Field(default=ChatChannel.text)
    title: Optional[str] = None
    description: Optional[str] = None
    grade: Optional[int] = None
    subject: Optional[str] = None


class ChatSessionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    grade: Optional[int] = None
    subject: Optional[str] = None


class ChatSessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    mode: ChatMode
    channel: ChatChannel
    title: Optional[str] = None
    description: Optional[str] = None
    grade: Optional[int] = None
    subject: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SessionResourceAttach(BaseModel):
    resource_ids: list[UUID]
