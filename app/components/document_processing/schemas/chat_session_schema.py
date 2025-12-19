from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID
from enum import Enum


class ChatModeEnum(str, Enum):
    learning = "learning"
    evaluation = "evaluation"


class ChatChannelEnum(str, Enum):
    text = "text"
    voice = "voice"
    mixed = "mixed"


class ChatSessionCreate(BaseModel):
    mode: ChatModeEnum = ChatModeEnum.learning
    channel: ChatChannelEnum = ChatChannelEnum.text
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
    mode: ChatModeEnum
    channel: ChatChannelEnum
    title: Optional[str]
    description: Optional[str]
    grade: Optional[int]
    subject: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
