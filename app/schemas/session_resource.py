# app/schemas/session_resource.py

from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class SessionResourceCreate(BaseModel):
    session_id: UUID
    resource_id: UUID
    label: Optional[str] = None


class SessionResourceResponse(BaseModel):
    session_id: UUID
    resource_id: UUID
    label: Optional[str]

    class Config:
        from_attributes = True
