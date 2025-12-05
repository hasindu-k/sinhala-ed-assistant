# app/components/document_processing/routers/ocr_router.py

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.components.document_processing.services.ocr_service import process_ocr_file

router = APIRouter()

@router.post("/ocr")
async def run_ocr(file: UploadFile = File(...)):
    """
    Basic OCR endpoint.
    Right now: dummy implementation.
    Later: connect Tesseract / TrOCR here.
    """
    if not file.content_type.startswith("image/") and "pdf" not in file.content_type:
        raise HTTPException(status_code=400, detail="Only image/PDF files are supported")

    result = await process_ocr_file(file)
    return result
