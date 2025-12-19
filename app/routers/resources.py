from fastapi import APIRouter, UploadFile, File
from uuid import UUID
from app.schemas.resource import (
    ResourceFileResponse,
    ResourceFileUpdate,
    ResourceUploadResponse,
    ResourceProcessResponse
)
from typing import List

router = APIRouter()


@router.post("/upload", response_model=ResourceUploadResponse)
def upload_resource(file: UploadFile = File(...)):
    """
    Upload a resource file (PDF, image, audio).
    """
    pass


@router.get("/", response_model=List[ResourceFileResponse])
def list_resources():
    """
    List all resources for the current user.
    """
    pass


@router.get("/{resource_id}", response_model=ResourceFileResponse)
def get_resource(resource_id: UUID):
    """
    Get resource metadata.
    """
    pass


# @router.put("/{resource_id}", response_model=ResourceFileResponse)
# def update_resource(resource_id: UUID, payload: ResourceFileUpdate):
#     """
#     Update resource metadata.
#     """
#     pass


@router.delete("/{resource_id}")
def delete_resource(resource_id: UUID):
    """
    Delete a resource file.
    """
    pass


@router.post("/{resource_id}/process", response_model=ResourceProcessResponse)
def process_resource(resource_id: UUID):
    """
    OCR, chunk, and embed a resource.
    """
    pass
