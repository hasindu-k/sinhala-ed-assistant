# app/components/document_processing/services/ocr_service.py

from fastapi import UploadFile

# later: import cv2, pytesseract, transformers, etc.
# from PIL import Image
# import pytesseract

async def process_ocr_file(file: UploadFile) -> str:
    """
    Stub for OCR processing.
    TODO: 
    - Save file to temp
    - Run Tesseract or TrOCR
    - Clean text
    """
    # For now, just return filename to confirm flow works.
    content = await file.read()
    size_kb = round(len(content) / 1024, 2)
    return f"[OCR placeholder] Received file '{file.filename}' ({size_kb} KB)."
