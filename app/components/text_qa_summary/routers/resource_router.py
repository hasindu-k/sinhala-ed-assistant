# app/components/text_qa_summary/routers/resource_router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime

from app.core.database import get_db
from app.shared.models.resource_data import ResourceData
from app.shared.models.user_chat import UserChat
from app.shared.models.text_chunk import TextChunk
from app.components.text_qa_summary.services.chunking_service import ChunkingService
from app.components.text_qa_summary.services.embedding_service import EmbeddingService
from app.core.config import settings

router = APIRouter()

# Request model
class ResourceUploadRequest(BaseModel):
    chat_id: str
    user_id: str
    resource_text: str

# Response model
class ResourceUploadResponse(BaseModel):
    id: str
    chat_id: str
    user_id: str
    created_at: str

# In your existing resource_router.py, update the upload_resource function:
@router.post("/upload", response_model=ResourceUploadResponse)
def upload_resource(request: ResourceUploadRequest, db: Session = Depends(get_db)):
    """
    Upload resource text (OCR output or manual text) for a chat
    """
    print(f"\n{'='*60}")
    print(f"RESOURCE UPLOAD START: chat={request.chat_id}, user={request.user_id}")
    print(f"{'='*60}")
    
    try:
        # Convert string to UUID
        try:
            chat_uuid = uuid.UUID(request.chat_id)
            print(f"✓ Chat ID converted to UUID: {chat_uuid}")
        except ValueError:
            print(f"✗ Invalid chat_id format: {request.chat_id}")
            raise HTTPException(status_code=400, detail="Invalid chat_id format")
        
        # Verify or create chat
        chat = db.query(UserChat).filter(UserChat.chat_id == chat_uuid).first()
        
        if not chat:
            chat = UserChat(
                chat_id=chat_uuid,
                user_id=request.user_id,
                title="Auto-created for resource upload"
            )
            db.add(chat)
            db.flush()
        
        # Create resource
        resource_id = uuid.uuid4()
        
        resource = ResourceData(
            id=resource_id,
            chat_id=chat_uuid,
            user_id=request.user_id,
            resource_text=request.resource_text
        )
        
        db.add(resource)
        db.flush()
        db.commit()
        
        # DEBUG: Check if TextChunk is accessible
        print(f"[DEBUG] Checking TextChunk accessibility...")
        print(f"[DEBUG] TextChunk class: {TextChunk}")
        print(f"[DEBUG] TextChunk table name: {TextChunk.__tablename__}")
        
        # Process resource into chunks
        print(f"[DEBUG] Starting chunking process...")
        chunks = ChunkingService.process_resource(db, resource_id, chat_uuid, request.user_id)
        print(f"[DEBUG] Created {len(chunks)} chunks")
        
        # Generate embeddings for chunks
        chunk_contents = [chunk.content for chunk in chunks]
        print(f"[DEBUG] Generating embeddings for {len(chunk_contents)} chunks...")
        embeddings = EmbeddingService.get_embeddings(chunk_contents)
        
        # Update chunks with embeddings
        print(f"[DEBUG] Updating chunks with embeddings...")
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding
            chunk.embedding_model = settings.MODEL_EMBEDDING_NAME
        
        db.commit()
        
        # Verify everything was saved
        saved_resource = db.query(ResourceData).filter(ResourceData.id == resource_id).first()
        saved_chunks = db.query(TextChunk).filter(TextChunk.resource_id == resource_id).count()
        
        if saved_resource:
            print(f"✅ RESOURCE SAVED SUCCESSFULLY!")
            print(f"   ID: {saved_resource.id}")
            print(f"   Chat ID: {saved_resource.chat_id}")
            print(f"   User: {saved_resource.user_id}")
            print(f"   Text length: {len(saved_resource.resource_text)}")
            print(f"   Chunks created: {saved_chunks}")
        else:
            print(f"❌ RESOURCE NOT FOUND IN DATABASE AFTER COMMIT!")
            raise HTTPException(status_code=500, detail="Resource was not saved to database")
        
        # Count totals
        total_resources = db.query(ResourceData).count()
        total_chunks = db.query(TextChunk).count()
        print(f"✓ Total resources in database: {total_resources}")
        print(f"✓ Total chunks in database: {total_chunks}")
        
        return ResourceUploadResponse(
            id=str(resource.id),
            chat_id=str(resource.chat_id),
            user_id=resource.user_id,
            created_at=resource.created_at.isoformat() if resource.created_at else datetime.now().isoformat()
        )
        
    except HTTPException as he:
        print(f"⛔ HTTPException: {he.detail}")
        db.rollback()
        raise he
    except Exception as e:
        print(f"⛔ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to upload resource: {str(e)}")
    finally:
        print(f"{'='*60}")
        print(f"RESOURCE UPLOAD END")
        print(f"{'='*60}\n")
              
@router.get("/list-all")
def list_all_resources(db: Session = Depends(get_db)):
    """List all resources (for debugging)"""
    try:
        resources = db.query(ResourceData).all()
        print(f"Database query returned {len(resources)} resources")
        return {
            "total": len(resources),
            "resources": [
                {
                    "id": str(res.id),
                    "chat_id": str(res.chat_id),
                    "user_id": res.user_id,
                    "preview": res.resource_text[:100] + "..." if len(res.resource_text) > 100 else res.resource_text,
                    "created_at": res.created_at.isoformat() if res.created_at else None
                }
                for res in resources
            ]
        }
    except Exception as e:
        print(f"Error in list-all: {e}")
        return {"error": str(e)}

@router.get("/test-db")
def test_database(db: Session = Depends(get_db)):
    """Test database connection and counts"""
    try:
        chat_count = db.query(UserChat).count()
        resource_count = db.query(ResourceData).count()
        
        return {
            "status": "connected",
            "user_chats": chat_count,
            "resources": resource_count,
            "message": f"Database has {chat_count} chats and {resource_count} resources"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}