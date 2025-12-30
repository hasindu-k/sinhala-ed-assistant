# app/utils/file_validation.py
from fastapi import UploadFile, File, HTTPException, status
from typing import List

# Allowed MIME types and corresponding friendly names
ALLOWED_TYPES = {
    "application/pdf": "PDF",
    "image/png": "PNG image",
    "image/jpeg": "JPEG image",
    "audio/mpeg": "MP3 audio"
}

MAX_SIZE_MB = 8 
MAX_SIZE = MAX_SIZE_MB * 1024 * 1024  # 5MB
MAX_FILES = 10

async def validate_files(
    files: List[UploadFile] = File(...)
) -> List[UploadFile]:
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files were uploaded."
        )

    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files uploaded. Maximum allowed is {MAX_FILES}."
        )

    for f in files:
        # --- Validate file type ---
        if f.content_type not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Unsupported file type for '{f.filename}'. "
                    f"Allowed types: {', '.join(ALLOWED_TYPES.values())}."
                )
            )

        # --- Validate file size ---
        contents = await f.read()
        if len(contents) > MAX_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'{f.filename}' exceeds the maximum size of {MAX_SIZE_MB} MB."
            )

        # --- Reset pointer so it can be read later ---
        await f.seek(0)

    return files
