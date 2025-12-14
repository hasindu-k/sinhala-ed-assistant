# app/components/text_qa_summary/routers/text_qa_router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import uuid

from app.core.database import get_db
from app.components.text_qa_summary.services.resource_service import ResourceService
from app.components.text_qa_summary.services.text_qa_service import TextQAService

router = APIRouter()

# Request models
class TextQAGenerateRequest(BaseModel):
    chat_id: str
    user_id: str
    count: int = 10

class SummaryGenerateRequest(BaseModel):
    chat_id: str
    user_id: str
    grade: str = "9-11"

# Response models
class TextQAResponse(BaseModel):
    message_id: str
    chat_id: str
    content: str
    safety_checks: dict

class SummaryResponse(BaseModel):
    message_id: str
    chat_id: str
    content: str
    safety_checks: dict

@router.post("/generate-qa", response_model=TextQAResponse)
def generate_qa(request: TextQAGenerateRequest, db: Session = Depends(get_db)):
    """
    Generate Q&A pairs from chat resources
    """
    try:
        # Convert string to UUID
        try:
            chat_uuid = uuid.UUID(request.chat_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid chat_id format")
        
        # Get combined resources text
        combined_text = ResourceService.get_combined_text(db, chat_uuid)
        
        # Generate Q&A
        message, safety_checks = TextQAService.generate_qa(
            db=db,
            chat_id=chat_uuid,
            user_id=request.user_id,
            combined_text=combined_text,
            count=request.count
        )
        
        return TextQAResponse(
            message_id=str(message.id),
            chat_id=str(message.chat_id),
            content=message.final_output,
            safety_checks=safety_checks
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@router.post("/generate-summary", response_model=SummaryResponse)
def generate_summary(request: SummaryGenerateRequest, db: Session = Depends(get_db)):
    """
    Generate adaptive summary from chat resources
    """
    try:
        # Convert string to UUID
        try:
            chat_uuid = uuid.UUID(request.chat_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid chat_id format")
        
        print(f"[DEBUG] Generating summary for chat: {chat_uuid}")
        
        # Get combined resources text
        try:
            combined_text = ResourceService.get_combined_text(db, chat_uuid)
            print(f"[DEBUG] Got combined text, length: {len(combined_text)}")
        except ValueError as e:
            print(f"[DEBUG] ResourceService error: {e}")
            # List all resources for debugging
            resources = ResourceService.get_chat_resources(db, chat_uuid)
            print(f"[DEBUG] Resources found: {len(resources)}")
            for r in resources:
                print(f"[DEBUG] Resource ID: {r.id}, Chat ID: {r.chat_id}")
            raise HTTPException(status_code=404, detail=str(e))
        
        # Generate summary
        message, safety_checks = TextQAService.generate_summary(
            db=db,
            chat_id=chat_uuid,
            user_id=request.user_id,
            combined_text=combined_text,
            grade=request.grade
        )
        
        return SummaryResponse(
            message_id=str(message.id),
            chat_id=str(message.chat_id),
            content=message.final_output,
            safety_checks=safety_checks
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")

@router.get("/{chat_id}/messages")
def get_chat_messages(chat_id: str, db: Session = Depends(get_db)):
    """
    Get all generated messages for a chat
    """
    try:
        chat_uuid = uuid.UUID(chat_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid chat_id format")
    
    messages = TextQAService.get_chat_messages(db, chat_uuid)
    
    return {
        "messages": [
            {
                "id": str(msg.id),
                "chat_id": str(msg.chat_id),
                "user_id": msg.user_id,
                "role": msg.role,
                "prompt_original": msg.prompt_original,
                "prompt_cleaned": msg.prompt_cleaned,
                "model_raw_output": msg.model_raw_output,
                "final_output": msg.final_output,
                "safety_missing_concepts": msg.safety_missing_concepts,
                "safety_extra_concepts": msg.safety_extra_concepts,
                "safety_flagged_sentences": msg.safety_flagged_sentences,
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            } for msg in messages
        ]
    }

# Add a test endpoint
@router.get("/test")
def test_qa_endpoint():
    return {"message": "Text QA router is working!"}