import os
from pathlib import Path
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.resource_repository import ResourceRepository
from app.shared.models.resource_file import ResourceFile

# Configure upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


class ResourceService:
    """Business logic for resources (files)."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = ResourceRepository(db)

    def validate_file_upload(self, filename: Optional[str], content_type: Optional[str], content: bytes):
        """Validate file upload requirements."""
        if not filename:
            raise ValueError("No filename provided")
        
        if not content_type:
            raise ValueError("No content type provided")
        
        if not content:
            raise ValueError("Empty file uploaded")

    def save_file_to_disk(self, user_id: UUID, filename: str, content: bytes) -> Path:
        """Save uploaded file to disk with safe naming."""
        safe_filename = f"{user_id}_{filename}"
        file_path = UPLOAD_DIR / safe_filename
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        return file_path

    def upload_resource_from_file(
        self,
        user_id: UUID,
        filename: str,
        content_type: str,
        content: bytes,
    ):
        """Handle complete file upload process with validation."""
        # Validate
        self.validate_file_upload(filename, content_type, content)
        
        # Save to disk
        try:
            file_path = self.save_file_to_disk(user_id, filename, content)
        except Exception as e:
            raise ValueError(f"Failed to save file: {e}")
        
        # Create database record
        try:
            resource = self.repository.upload_resource(
                user_id=user_id,
                original_filename=filename,
                storage_path=str(file_path),
                mime_type=content_type,
                size_bytes=len(content),
                source_type="user_upload",
            )
            return resource
        except Exception as e:
            # Cleanup file if database save failed
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception:
                    pass
            raise

    def upload_resource(
        self,
        user_id: UUID,
        original_filename: Optional[str],
        storage_path: Optional[str],
        mime_type: Optional[str],
        size_bytes: Optional[int],
        source_type: Optional[str] = None,
        language: Optional[str] = None,
    ):
        return self.repository.upload_resource(
            user_id=user_id,
            original_filename=original_filename,
            storage_path=storage_path,
            mime_type=mime_type,
            size_bytes=size_bytes,
            source_type=source_type,
            language=language,
        )

    def get_resource(self, resource_id: UUID):
        return self.repository.get_resource(resource_id)

    def list_user_resources(self, user_id: UUID) -> List:
        return self.repository.list_user_resources(user_id)
    
    def get_resource_with_ownership_check(self, resource_id: UUID, user_id: UUID):
        """Get resource and verify ownership."""
        resource = self.repository.get_resource(resource_id)
        if not resource:
            raise ValueError("Resource not found")
        
        if resource.user_id != user_id:
            raise PermissionError("You don't have permission to access this resource")
        
        return resource
    
    def update_resource(
        self,
        resource_id: UUID,
        user_id: UUID,
        original_filename: Optional[str] = None,
        language: Optional[str] = None,
    ):
        """Update resource after ownership validation."""
        resource = self.get_resource_with_ownership_check(resource_id, user_id)
        
        # Update fields
        if original_filename is not None:
            resource.original_filename = original_filename
        if language is not None:
            resource.language = language
        
        self.db.commit()
        self.db.refresh(resource)
        return resource
    
    def delete_resource(self, resource_id: UUID, user_id: UUID):
        """Delete resource and associated file after ownership validation."""
        resource = self.get_resource_with_ownership_check(resource_id, user_id)
        
        # Delete physical file
        if resource.storage_path and os.path.exists(resource.storage_path):
            try:
                os.remove(resource.storage_path)
            except Exception as file_error:
                # Log but don't fail the operation
                pass
        
        # Delete database record
        self.db.delete(resource)
        self.db.commit()
    
    def process_resource(self, resource_id: UUID, user_id: UUID):
        """Process resource (OCR, chunk, embed) after validation."""
        resource = self.get_resource_with_ownership_check(resource_id, user_id)
        
        # Check if resource file exists
        if not resource.storage_path or not os.path.exists(resource.storage_path):
            raise ValueError("Resource file not found on disk")
        
        # TODO: Implement actual OCR, chunking, and embedding logic here
        # For now, return a placeholder response
        
        return {
            "resource_id": resource_id,
            "status": "processing",
            "chunks_created": 0,
            "message": "Processing initiated successfully"
        }
