from fastapi import APIRouter, UploadFile, File
from uuid import UUID

router = APIRouter()


@router.post("/upload")
def upload_resource(file: UploadFile = File(...)):
    """
    Upload a resource file (PDF, image, audio).
    """
    pass


@router.post("/{resource_id}/process")
def process_resource(resource_id: UUID):
    """
    OCR, chunk, and embed a resource.
    """
    pass


@router.get("/{resource_id}")
def get_resource(resource_id: UUID):
    """
    Get resource metadata.
    """
    pass
