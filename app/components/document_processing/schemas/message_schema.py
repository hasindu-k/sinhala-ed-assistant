from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from enum import Enum


class MessageRoleEnum(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class MessageModalityEnum(str, Enum):
    text = "text"
    voice = "voice"


class GradeLevelEnum(str, Enum):
    middle = "6 - 8"
    secondary = "9 - 11"
    advanced = "12 - 13"
    university = "university"


class MessageCreate(BaseModel):
    session_id: UUID
    role: MessageRoleEnum
    modality: MessageModalityEnum = MessageModalityEnum.text
    content: Optional[str] = None
    grade_level: Optional[GradeLevelEnum] = None
    audio_url: Optional[str] = None
    transcript: Optional[str] = None
    audio_duration_sec: Optional[float] = None
    model_name: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


class MessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    role: MessageRoleEnum
    modality: MessageModalityEnum
    content: Optional[str]
    grade_level: Optional[GradeLevelEnum]
    audio_url: Optional[str]
    transcript: Optional[str]
    audio_duration_sec: Optional[float]
    model_name: Optional[str]
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    total_tokens: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True
