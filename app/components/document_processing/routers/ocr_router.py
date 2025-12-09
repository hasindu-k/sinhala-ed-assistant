# app/components/document_processing/routers/ocr_router.py

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from app.components.document_processing.services.ocr_service import process_ocr_file, process_question_papers
from app.core.database import get_db
from app.shared.ai.embeddings import model_list

router = APIRouter()

@router.post("/ocr")
async def run_ocr(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    OCR endpoint for images and PDFs.
    """
    if not file.content_type.startswith("image/") and "pdf" not in file.content_type:
        raise HTTPException(status_code=400, detail="Only image/PDF files are supported")

    result = await process_ocr_file(file, db=db)
    return result

@router.post("/model-test")
async def model_test():
    """
    Model testing endpoint.
    """
    model_list()
    return {"message": "Model test successful"} 

@router.post("/scan-papers")
async def scan_papers(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Endpoint to scan and process exam papers.
    """
    if not file.content_type.startswith("image/") and "pdf" not in file.content_type:
        raise HTTPException(status_code=400, detail="Only image/PDF files are supported")

    result = await process_question_papers(file, db=db)
    return result
