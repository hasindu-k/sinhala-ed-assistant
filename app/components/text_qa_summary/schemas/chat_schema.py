#app/components/text_qa_summary/schemas/chat_schema.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid as uuid_pkg


class ChatCreateRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    title: Optional[str] = Field(None, description="Optional chat title")


class ChatCreateResponse(BaseModel):
    chat_id: uuid_pkg.UUID = Field(..., description="Created chat session ID")
    user_id: str = Field(..., description="User ID")
    title: Optional[str] = Field(None, description="Chat title")
    created_at: datetime = Field(..., description="Creation timestamp")


class ChatResponse(BaseModel):
    chat_id: uuid_pkg.UUID = Field(..., description="Chat session ID")
    user_id: str = Field(..., description="User ID")
    title: Optional[str] = Field(None, description="Chat title")
    created_at: datetime = Field(..., description="Creation timestamp")


class ChatListResponse(BaseModel):
    chats: list[ChatResponse] = Field(..., description="List of user chats")