# app/schemas/resource.py

from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime
from enum import Enum


class ResourceSource(str, Enum):
    user_upload = "user_upload"
    url = "url"
    system = "system"


class ResourceFileCreate(BaseModel):
    original_filename: Optional[str] = None
    storage_path: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    source_type: Optional[ResourceSource] = None
    language: Optional[str] = None


class ResourceFileUpdate(BaseModel):
    original_filename: Optional[str] = None
    language: Optional[str] = None


class ResourceFileResponse(BaseModel):
    id: UUID
    user_id: UUID
    original_filename: Optional[str] = None
    storage_path: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    source_type: Optional[ResourceSource] = None
    language: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ResourceUploadResponse(BaseModel):
    resource_id: UUID
    filename: str
    size_bytes: int
    mime_type: str


class ResourceBulkUploadResponse(BaseModel):
    uploads: list[ResourceUploadResponse]


class ResourceProcessRequest(BaseModel):
    resource_id: UUID


class ResourceProcessResponse(BaseModel):
    resource_id: UUID
    status: str
    chunks_created: Optional[int] = None
    message: Optional[str] = None
