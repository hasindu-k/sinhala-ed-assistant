# app/components/text_qa_summary/services/chat_service.py
import uuid
from sqlalchemy.orm import Session
from app.shared.models.user_chat import UserChat
from app.components.text_qa_summary.schemas.chat_schema import ChatCreateRequest


class ChatService:
    @staticmethod
    def create_chat(db: Session, request: ChatCreateRequest) -> UserChat:
        chat = UserChat(
            chat_id=uuid.uuid4(),
            user_id=request.user_id,
            title=request.title
        )
        db.add(chat)
        db.commit()
        db.refresh(chat)
        return chat

    @staticmethod
    def get_chat_by_id(db: Session, chat_id: uuid.UUID) -> UserChat:
        return db.query(UserChat).filter(UserChat.chat_id == chat_id).first()

    @staticmethod
    def get_user_chats(db: Session, user_id: str) -> list[UserChat]:
        return db.query(UserChat).filter(UserChat.user_id == user_id).order_by(UserChat.created_at.desc()).all()

    @staticmethod
    def delete_chat(db: Session, chat_id: uuid.UUID, user_id: str) -> bool:
        chat = db.query(UserChat).filter(
            UserChat.chat_id == chat_id,
            UserChat.user_id == user_id
        ).first()
        
        if chat:
            db.delete(chat)
            db.commit()
            return True
        return False