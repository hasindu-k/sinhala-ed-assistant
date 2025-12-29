# app/components/text_qa_summary/services/resource_service.py
import uuid
from sqlalchemy.orm import Session
from app.shared.models.resource_data import ResourceData
from app.shared.models.user_chat import UserChat


class ResourceService:
    @staticmethod
    def upload_resource(db: Session, chat_id: uuid.UUID, user_id: str, resource_text: str) -> ResourceData:
        # Verify chat exists
        chat = db.query(UserChat).filter(UserChat.chat_id == chat_id).first()
        if not chat:
            raise ValueError(f"Chat {chat_id} not found")
        
        resource = ResourceData(
            id=uuid.uuid4(),
            chat_id=chat_id,
            user_id=user_id,
            resource_text=resource_text
        )
        db.add(resource)
        db.commit()
        db.refresh(resource)
        return resource

    @staticmethod
    def get_chat_resources(db: Session, chat_id: uuid.UUID) -> list[ResourceData]:
        resources = db.query(ResourceData).filter(ResourceData.chat_id == chat_id).order_by(ResourceData.created_at).all()
        print(f"[DEBUG] Found {len(resources)} resources for chat {chat_id}")
        return resources

    @staticmethod
    def get_combined_text(db: Session, chat_id: uuid.UUID) -> str:
        resources = ResourceService.get_chat_resources(db, chat_id)
        if not resources:
            raise ValueError(f"No resources found for chat {chat_id}")
        
        # Combine all resources with a separator
        combined = "\n\n".join([r.resource_text for r in resources])
        print(f"[DEBUG] Combined text length: {len(combined)}")
        return combined

    @staticmethod
    def delete_resource(db: Session, resource_id: uuid.UUID, user_id: str) -> bool:
        resource = db.query(ResourceData).filter(
            ResourceData.id == resource_id,
            ResourceData.user_id == user_id
        ).first()
        
        if resource:
            db.delete(resource)
            db.commit()
            return True
        return False