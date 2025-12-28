# app/components/text_qa_summary/routers/text_qa_router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid

from app.core.database import get_db
from app.components.text_qa_summary.services.resource_service import ResourceService
from app.components.text_qa_summary.services.text_qa_service import TextQAService
from app.components.text_qa_summary.schemas.text_qa_schema import (
    TextQAGenerateRequest,
    SummaryGenerateRequest,
    TextQAResponse,
    SummaryResponse,
)

router = APIRouter()

@router.post("/generate-qa", response_model=TextQAResponse)
def generate_qa(request: TextQAGenerateRequest, db: Session = Depends(get_db)):
    """
    Generate Q&A pairs from RETRIEVED chat resources
    """
    try:
        # Use pydantic-parsed UUID
        chat_uuid = request.chat_id

        print(f"[API] Q&A generation request: {request.query}")

        # Generate Q&A with retrieval
        message, safety_checks = TextQAService.generate_qa(
            db=db,
            chat_id=chat_uuid,
            user_id=request.user_id,
            query=request.query,
            count=request.count,
        )
        
        return TextQAResponse(
            message_id=message.id,
            chat_id=message.chat_id,
            content=message.final_output,
            safety_checks=safety_checks,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@router.post("/generate-summary", response_model=SummaryResponse)
def generate_summary(request: SummaryGenerateRequest, db: Session = Depends(get_db)):
    """
    Generate adaptive summary from RETRIEVED chat resources
    """
    try:
        # Use pydantic-parsed UUID
        chat_uuid = request.chat_id

        print(f"[API] Summary generation request: {request.query}")
        print(f"[API] Grade level: {request.grade}")

        # Generate summary with retrieval
        message, safety_checks = TextQAService.generate_summary(
            db=db,
            chat_id=chat_uuid,
            user_id=request.user_id,
            query=request.query,
            grade=request.grade,
        )
        
        return SummaryResponse(
            message_id=message.id,
            chat_id=message.chat_id,
            content=message.final_output,
            safety_checks=safety_checks,
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")
        
@router.get("/{chat_id}/messages")
def get_chat_messages(chat_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Get all generated messages for a chat
    """
    messages = TextQAService.get_chat_messages(db, chat_id)
    
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