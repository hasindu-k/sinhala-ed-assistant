# app/components/document_processing/utils/file_loader.py

import os
import tempfile
from fastapi import UploadFile

import logging
logger = logging.getLogger(__name__)

async def save_upload_to_temp(file: UploadFile) -> str:
    """
    Save uploaded file to a temp location and return the path.
    """
    suffix = f"_{file.filename}"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        return tmp.name
    
def remove_temp_file(temp_path: str):
    """
    Remove the temporary file after processing.
    """
    try:
        os.remove(temp_path)
    except Exception as e:
        logger.warning("Failed to remove temp file %s: %s", temp_path, e)

def convert_file_to_images(file_path: str, ext: str):
    """
    Convert a file (PDF or image) to a list of images.
    """
    from pdf2image import convert_from_path
    from PIL import Image

    images = []
    if ext == "pdf":
        images = convert_from_path(file_path)
    elif ext in {"png", "jpg", "jpeg", "tiff", "webp"}:
        img = Image.open(file_path)
        images.append(img)
    return images