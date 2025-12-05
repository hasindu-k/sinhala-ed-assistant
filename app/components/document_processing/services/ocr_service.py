# app/components/document_processing/services/ocr_service.py

import os
from fastapi import UploadFile
import cv2
import numpy as np
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
from app.models.document import OCRDocument

from app.models.document import OCRDocument
from app.components.document_processing.utils.file_loader import save_upload_to_temp
from app.components.document_processing.services.embedding_service import (
    embed_chunks,
    embed_document_text,
)

async def process_ocr_file(file: UploadFile) -> dict:
    """
    Full OCR pipeline:
    1. Save uploaded file to temporary location
    2. Detect PDF or image
    3. Convert PDF pages -> images (if PDF)
    4. Run Tesseract OCR on each page
    5. Clean + chunk + embed text with Gemini
    6. Insert OCRDocument into DB
    7. Return structured response
    """

    # 1. Save file to temp
    temp_path = await save_upload_to_temp(file)
    ext = file.filename.split(".")[-1].lower()

    # 2. Detect PDF or image
    is_pdf = ext == "pdf"

    if is_pdf:
        images = convert_from_path(temp_path)  # List of PIL images
    else:
        images = [Image.open(temp_path)]       # Single PIL image

    extracted_text = ""
    page_count = 0

    for pil_img in images:
        page_count += 1

        # -----------------------------
        # Convert PIL → OpenCV (BGR)
        # -----------------------------
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Run OCR
        text = pytesseract.image_to_string(gray, lang="sin+eng")

        extracted_text += f"\n\n--- PAGE {page_count} ---\n{text}"
    
    # 3. Generate chunk-level embeddings (clean + chunk inside)
    embedded_chunks = await embed_chunks(extracted_text)
    
    # 4. Generate a single full-document embedding (for global search)
    full_embedding = embed_document_text(extracted_text)

    # 5. Build OCRDocument model and insert into DB
    doc = OCRDocument(
    filename=file.filename,
    full_text=extracted_text,
    pages=page_count,
    chunks=embedded_chunks  # list of {chunk_id,text,embedding}
    )

    await doc.insert()

    # 6. Try to remove temp file
    try:
        os.remove(temp_path)
    except Exception as e:
        print(f"[WARN] Failed to remove temp file {temp_path}: {e}")

    # 7. Return results
    return {
        "filename": file.filename,
        "pages": page_count,
        "text": extracted_text.strip(),
        # full-document embedding info
        "embedding_dim": len(full_embedding) if full_embedding else 0,
        "embedding": full_embedding,
        # chunk-level embeddings (for RAG)
        "chunks": embedded_chunks,
    }
