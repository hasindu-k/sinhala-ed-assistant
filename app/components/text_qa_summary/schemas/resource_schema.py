#app/components/text_qa_summary/schemas/resource_schema.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid as uuid_pkg


class ResourceUploadRequest(BaseModel):
    chat_id: uuid_pkg.UUID = Field(..., description="Chat session ID")
    user_id: str = Field(..., description="User ID")
    resource_text: str = Field(..., description="OCR output or manual text")


class ResourceUploadResponse(BaseModel):
    id: uuid_pkg.UUID = Field(..., description="Resource ID")
    chat_id: uuid_pkg.UUID = Field(..., description="Chat session ID")
    user_id: str = Field(..., description="User ID")
    created_at: datetime = Field(..., description="Creation timestamp")


class ResourceResponse(BaseModel):
    id: uuid_pkg.UUID = Field(..., description="Resource ID")
    chat_id: uuid_pkg.UUID = Field(..., description="Chat session ID")
    user_id: str = Field(..., description="User ID")
    resource_text: str = Field(..., description="Resource content")
    created_at: datetime = Field(..., description="Creation timestamp")


class ResourceListResponse(BaseModel):
    resources: list[ResourceResponse] = Field(..., description="List of resources")
