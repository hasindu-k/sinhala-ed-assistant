from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
import uuid as uuid_pkg


class MessageResponse(BaseModel):
    id: uuid_pkg.UUID = Field(..., description="Message ID")
    chat_id: uuid_pkg.UUID = Field(..., description="Chat session ID")
    user_id: str = Field(..., description="User ID")
    role: str = Field(..., description="Role: user or teacher")
    prompt_original: str = Field(..., description="Original prompt")
    prompt_cleaned: Optional[str] = Field(None, description="Cleaned prompt")
    model_raw_output: str = Field(..., description="Raw model output")
    final_output: str = Field(..., description="Final output after safety checks")
    safety_missing_concepts: Optional[List[str]] = Field(None, description="Missing concepts")
    safety_extra_concepts: Optional[List[str]] = Field(None, description="Extra concepts")
    safety_flagged_sentences: Optional[List[Any]] = Field(None, description="Flagged sentences")
    created_at: datetime = Field(..., description="Creation timestamp")


class MessageListResponse(BaseModel):
    messages: list[MessageResponse] = Field(..., description="List of messages")