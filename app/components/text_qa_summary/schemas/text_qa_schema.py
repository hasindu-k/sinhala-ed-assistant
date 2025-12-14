#app/components/text_qa_summary/schemas/text_qa_schema.py
from pydantic import BaseModel, Field
from typing import Optional
import uuid as uuid_pkg


class TextQAGenerateRequest(BaseModel):
    chat_id: uuid_pkg.UUID = Field(..., description="Chat session ID")
    user_id: str = Field(..., description="User ID")
    count: int = Field(default=10, ge=1, le=50, description="Number of Q&A pairs to generate")


class SummaryGenerateRequest(BaseModel):
    chat_id: uuid_pkg.UUID = Field(..., description="Chat session ID")
    user_id: str = Field(..., description="User ID")
    grade: str = Field(
        default="9-11", 
        description="Grade level: 6-8, 9-11, 12-13, university"
    )


class TextQAResponse(BaseModel):
    message_id: uuid_pkg.UUID = Field(..., description="Generated message ID")
    chat_id: uuid_pkg.UUID = Field(..., description="Chat session ID")
    content: str = Field(..., description="Generated Q&A content")
    safety_checks: dict = Field(..., description="Safety check results")


class SummaryResponse(BaseModel):
    message_id: uuid_pkg.UUID = Field(..., description="Generated message ID")
    chat_id: uuid_pkg.UUID = Field(..., description="Chat session ID")
    content: str = Field(..., description="Generated summary content")
    safety_checks: dict = Field(..., description="Safety check results")