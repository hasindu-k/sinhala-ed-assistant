# # app/components/text_qa_summary/routers/chat_router.py
# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session
# import uuid
# from datetime import datetime

# from app.core.database import get_db
# from app.shared.models.user_chat import UserChat
# from app.components.text_qa_summary.schemas.chat_schema import (
#     ChatCreateRequest,
#     ChatCreateResponse,
# )

# router = APIRouter()

# @router.post("/create", response_model=ChatCreateResponse)
# def create_chat(request: ChatCreateRequest, db: Session = Depends(get_db)):
#     """
#     Create a new chat session
#     """
#     try:
#         # Generate UUID
#         new_chat_id = uuid.uuid4()
#         print(f"[DEBUG] Attempting to create chat with ID: {new_chat_id}")

#         # Create chat object
#         chat = UserChat(
#             chat_id=new_chat_id,
#             user_id=request.user_id,
#             title=request.title
#         )
        
#         # Add to session
#         db.add(chat)
#         print(f"[DEBUG] Chat added to session")
        
#         # Commit transaction
#         db.commit()
#         print(f"[DEBUG] Transaction committed")
        
#         # Refresh to get database-generated values
#         db.refresh(chat)
#         print(f"[DEBUG] Chat refreshed from database")
        
#         # Verify the chat was saved
#         saved_chat = db.query(UserChat).filter(UserChat.chat_id == new_chat_id).first()
#         if not saved_chat:
#             print(f"[ERROR] Chat {new_chat_id} was not found after commit!")
#             raise HTTPException(status_code=500, detail="Chat was not saved to database")
        
#         print(f"[DEBUG] Chat verified in database: {saved_chat.chat_id}")
        
#         return ChatCreateResponse(
#             chat_id=chat.chat_id,
#             user_id=chat.user_id,
#             title=chat.title,
#             created_at=chat.created_at if chat.created_at else datetime.now()
#         )
        
#     except Exception as e:
#         print(f"[ERROR] Failed to create chat: {str(e)}")
#         db.rollback()  # Rollback on error
#         raise HTTPException(status_code=500, detail=f"Failed to create chat: {str(e)}")

# @router.get("/list-all")
# def list_all_chats(db: Session = Depends(get_db)):
#     """List all chats in database (for debugging)"""
#     try:
#         chats = db.query(UserChat).all()
#         return {
#             "total": len(chats),
#             "chats": [
#                 {
#                     "chat_id": str(chat.chat_id),
#                     "user_id": chat.user_id,
#                     "title": chat.title,
#                     "created_at": chat.created_at.isoformat() if chat.created_at else None
#                 }
#                 for chat in chats
#             ]
#         }
#     except Exception as e:
#         return {"error": str(e)}