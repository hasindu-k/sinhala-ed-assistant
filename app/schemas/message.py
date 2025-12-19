from pydantic import BaseModel
from typing import Optional
from enum import Enum


class MessageModality(str, Enum):
    text = "text"
    voice = "voice"


class MessageCreate(BaseModel):
    modality: MessageModality
    content: Optional[str] = None
    audio_url: Optional[str] = None
