import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from app.schemas.resource import (
    ResourceFileResponse,
    ResourceFileCreate,
    ResourceFileUpdate,
    ResourceUploadResponse,
    ResourceProcessResponse
)
from app.schemas.resource_chunk import ResourceChunkResponse
from app.services.resource_service import ResourceService
from app.services.resource_chunk_service import ResourceChunkService
from app.core.database import get_db
from app.core.security import get_current_user
from app.shared.models.user import User
from typing import List

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload", response_model=ResourceUploadResponse)
async def upload_resource(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a resource file (PDF, image, audio).
    
    Args:
        file: Uploaded file
        current_user: Authenticated user
        db: Database session
        
    Returns:
        ResourceUploadResponse with upload details
        
    Raises:
        HTTPException 400: Invalid file type or empty file
        HTTPException 500: File storage or database error
    """
    try:
        # Read file content
        content = await file.read()
        
        # Upload via service
        resource_service = ResourceService(db)
        resource = resource_service.upload_resource_from_file(
            user_id=current_user.id,
            filename=file.filename,
            content_type=file.content_type,
            content=content,
        )
        
        logger.info(f"Resource uploaded: {resource.id} ({file.filename}) by user {current_user.id}")
        
        return ResourceUploadResponse(
            resource_id=resource.id,
            filename=file.filename,
            size_bytes=len(content),
            mime_type=file.content_type,
        )
        
    except ValueError as e:
        logger.warning(f"Validation error uploading resource: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error uploading resource for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload resource"
        )


@router.get("/", response_model=List[ResourceFileResponse])
def list_resources(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all resources for the current user.
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of ResourceFileResponse objects
        
    Raises:
        HTTPException 500: Database error
    """
    try:
        resource_service = ResourceService(db)
        resources = resource_service.list_user_resources(current_user.id)
        
        logger.debug(f"Retrieved {len(resources)} resources for user {current_user.id}")
        return resources
        
    except Exception as e:
        logger.error(f"Error listing resources for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve resources"
        )


@router.get("/{resource_id}", response_model=ResourceFileResponse)
def get_resource(
    resource_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get resource metadata.
    
    Args:
        resource_id: ID of the resource
        current_user: Authenticated user
        db: Database session
        
    Returns:
        ResourceFileResponse with resource details
        
    Raises:
        HTTPException 403: User doesn't own the resource
        HTTPException 404: Resource not found
        HTTPException 500: Database error
    """
    try:
        resource_service = ResourceService(db)
        resource = resource_service.get_resource_with_ownership_check(resource_id, current_user.id)
        logger.debug(f"Retrieved resource {resource_id} for user {current_user.id}")
        return resource
        
    except ValueError as e:
        logger.warning(f"Resource {resource_id} not found for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"User {current_user.id} attempted unauthorized access to resource {resource_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error retrieving resource {resource_id} for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve resource"
        )


@router.get("/{resource_id}/chunks", response_model=List[ResourceChunkResponse])
def get_resource_chunks(
    resource_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all chunks for a resource (admin/debug use).
    
    Args:
        resource_id: ID of the resource
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of ResourceChunkResponse objects
        
    Raises:
        HTTPException 403: User doesn't own the resource
        HTTPException 404: Resource not found
        HTTPException 500: Database error
    """
    try:
        # Verify ownership
        resource_service = ResourceService(db)
        resource_service.get_resource_with_ownership_check(resource_id, current_user.id)
        
        # Get chunks
        chunk_service = ResourceChunkService(db)
        chunks = chunk_service.get_chunks_for_resource(resource_id)
        logger.debug(f"Retrieved {len(chunks)} chunks for resource {resource_id}")
        return chunks
        
    except ValueError as e:
        logger.warning(f"Resource {resource_id} not found for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"User {current_user.id} attempted unauthorized access to resource {resource_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error retrieving chunks for resource {resource_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chunks"
        )


@router.put("/{resource_id}", response_model=ResourceFileResponse)
def update_resource(
    resource_id: UUID,
    payload: ResourceFileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update resource metadata.
    
    Args:
        resource_id: ID of the resource to update
        payload: Resource update data
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Updated ResourceFileResponse
        
    Raises:
        HTTPException 403: User doesn't own the resource
        HTTPException 404: Resource not found
        HTTPException 500: Database error
    """
    try:
        resource_service = ResourceService(db)
        resource = resource_service.update_resource(
            resource_id=resource_id,
            user_id=current_user.id,
            original_filename=payload.original_filename,
            language=payload.language,
        )
        logger.info(f"Resource {resource_id} updated by user {current_user.id}")
        return resource
        
    except ValueError as e:
        logger.warning(f"Resource {resource_id} not found for update by user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"User {current_user.id} attempted unauthorized update to resource {resource_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating resource {resource_id} for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update resource"
        )


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource(
    resource_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a resource file.
    
    Args:
        resource_id: ID of the resource to delete
        current_user: Authenticated user
        db: Database session
        
    Raises:
        HTTPException 403: User doesn't own the resource
        HTTPException 404: Resource not found
        HTTPException 500: Database or file system error
    """
    try:
        resource_service = ResourceService(db)
        resource_service.delete_resource(resource_id, current_user.id)
        logger.info(f"Resource {resource_id} deleted by user {current_user.id}")
        
    except ValueError as e:
        logger.warning(f"Resource {resource_id} not found for deletion by user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"User {current_user.id} attempted unauthorized deletion of resource {resource_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting resource {resource_id} for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete resource"
        )


@router.post("/{resource_id}/process", response_model=ResourceProcessResponse)
def process_resource(
    resource_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    OCR, chunk, and embed a resource.
    
    Args:
        resource_id: ID of the resource to process
        current_user: Authenticated user
        db: Database session
        
    Returns:
        ResourceProcessResponse with processing results
        
    Raises:
        HTTPException 400: Resource already processed or invalid type
        HTTPException 403: User doesn't own the resource
        HTTPException 404: Resource not found
        HTTPException 500: Processing error
    """
    try:
        resource_service = ResourceService(db)
        result = resource_service.process_resource(resource_id, current_user.id)
        logger.info(f"Resource {resource_id} processing initiated by user {current_user.id}")
        return result
        
    except ValueError as e:
        logger.warning(f"Validation error processing resource {resource_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"User {current_user.id} attempted unauthorized processing of resource {resource_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error processing resource {resource_id} for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process resource"
        )
