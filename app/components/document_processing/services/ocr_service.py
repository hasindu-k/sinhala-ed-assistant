# app/components/document_processing/services/ocr_service.py

import os
from fastapi import UploadFile
import cv2
import numpy as np
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
from bson import ObjectId

from app.models.document import OCRDocument
from app.components.document_processing.utils.file_loader import save_upload_to_temp
from app.components.document_processing.utils.text_cleaner import basic_clean
from app.components.document_processing.services.embedding_service import (
    embed_chunks,
    embed_document_text,
)
from app.components.document_processing.services.classifier_service import classify_document


async def process_ocr_file(file: UploadFile) -> dict:
    """
    Full OCR pipeline:
    1. Save file
    2. Convert PDF → Images
    3. Run OCR (Sinhala + English)
    4. Clean text
    5. Classify document type
    6. Chunk + embed with numbering
    7. Insert into DB
    8. Return structured result
    """

    # -----------------------------
    # 1. Save uploaded file temporarily
    # -----------------------------
    temp_path = await save_upload_to_temp(file)
    ext = file.filename.split(".")[-1].lower()

    # -----------------------------
    # 2. Detect PDF or Image
    # -----------------------------
    if ext == "pdf":
        images = convert_from_path(temp_path)
    else:
        images = [Image.open(temp_path)]

    extracted_text = ""
    page_count = 0

    # -----------------------------
    # 3. OCR every page
    # -----------------------------
    for pil_img in images:
        page_count += 1

        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Sinhala + English OCR
        text = pytesseract.image_to_string(gray, lang="sin+eng")

        extracted_text += f"\n\n--- PAGE {page_count} ---\n{text}"

    # -----------------------------
    # 4. Clean OCR text before classification + chunking + embedding
    # -----------------------------
    cleaned_text = basic_clean(extracted_text)

    # -----------------------------
    # 5. Automatic Document Classifier
    # -----------------------------
    doc_type = classify_document(cleaned_text)

    # -----------------------------
    # 6. Generate doc_id BEFORE embeddings
    # -----------------------------
    doc_id = str(ObjectId())

    # -----------------------------
    # 7. Chunk-level embeddings (includes numbering + global_id)
    # -----------------------------
    embedded_chunks = embed_chunks(cleaned_text, doc_id=doc_id)

    # -----------------------------
    # 8. Full document embedding
    # -----------------------------
    full_embedding = embed_document_text(cleaned_text)

    # -----------------------------
    # 9. Save to Database
    # -----------------------------
    doc = OCRDocument(
        _id=doc_id,
        filename=file.filename,
        full_text=cleaned_text,
        pages=page_count,
        doc_type=doc_type,
        chunks=embedded_chunks
    )

    await doc.insert()

    # -----------------------------
    # 10. Remove temp file
    # -----------------------------
    try:
        os.remove(temp_path)
    except Exception as e:
        print(f"[WARN] Failed to remove temp file {temp_path}: {e}")

    # -----------------------------
    # 11. Return result to API
    # -----------------------------
    return {
        "doc_id": doc_id,
        "filename": file.filename,
        "pages": page_count,
        "doc_type": doc_type,
        "text": cleaned_text.strip(),
        # full-document embedding info
        "embedding_dim": len(full_embedding) if full_embedding else 0,
        "embedding": full_embedding,
        # chunk-level embeddings (for RAG)
        "chunks": embedded_chunks,
    }
