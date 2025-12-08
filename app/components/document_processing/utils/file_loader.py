# app/components/document_processing/utils/file_loader.py

import tempfile
from fastapi import UploadFile

async def save_upload_to_temp(file: UploadFile) -> str:
    """
    Save uploaded file to a temp location and return the path.
    """
    suffix = f"_{file.filename}"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        return tmp.name
