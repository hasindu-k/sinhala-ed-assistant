from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID
from enum import Enum


class ResourceSourceEnum(str, Enum):
    user_upload = "user_upload"
    url = "url"
    system = "system"


class ResourceFileCreate(BaseModel):
    original_filename: str
    mime_type: str
    size_bytes: int
    source_type: ResourceSourceEnum
    language: Optional[str] = None


class ResourceFileUpdate(BaseModel):
    language: Optional[str] = None


class ResourceFileResponse(BaseModel):
    id: UUID
    user_id: UUID
    original_filename: Optional[str]
    storage_path: Optional[str]
    mime_type: Optional[str]
    size_bytes: Optional[int]
    source_type: Optional[ResourceSourceEnum]
    language: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
