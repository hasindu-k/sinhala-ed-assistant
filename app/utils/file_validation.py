# app/utils/file_validation.py
from fastapi import UploadFile, File, HTTPException, status, Depends
from typing import List

ALLOWED_TYPES = {"application/pdf", "image/png", "image/jpeg", "audio/mpeg"}
MAX_SIZE_MB = 5 
MAX_SIZE = MAX_SIZE_MB * 1024 * 1024  # 5MB
MAX_FILES = 10


async def validate_files(
    files: List[UploadFile] = File(...)
) -> List[UploadFile]:

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files uploaded"
        )

    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files. Max allowed = {MAX_FILES}"
        )

    for f in files:
        if f.content_type not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {f.content_type}"
            )

        contents = await f.read()
        if len(contents) > MAX_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{f.filename} exceeds max size of {MAX_SIZE_MB} MB",
            )

        await f.seek(0)   # reset pointer so your handler can read again

    return files
