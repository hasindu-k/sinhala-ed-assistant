# app/components/document_processing/services/ocr_service.py

import os
from fastapi import UploadFile, Depends
import cv2
import numpy as np
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

from sqlalchemy.orm import Session
from app.database.models import OCRDocument, ChunkModel
from app.core.database import get_db
from app.components.document_processing.utils.file_loader import save_upload_to_temp
from app.components.document_processing.utils.text_cleaner import basic_clean
from app.components.document_processing.services.embedding_service import (
    embed_chunks,
    embed_document_text,
)
from app.components.document_processing.services.classifier_service import classify_document


async def process_ocr_file(file: UploadFile, db: Session = Depends(get_db)) -> dict:
    """
    Full OCR pipeline:
    1. Save file
    2. Convert PDF → Images
    3. Run OCR (Sinhala + English)
    4. Clean text
    5. Classify document type
    6. Chunk + embed with numbering
    7. Insert into DB (PostgreSQL via SQLAlchemy)
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

        text = pytesseract.image_to_string(gray, lang="sin+eng")
        extracted_text += f"\n\n--- PAGE {page_count} ---\n{text}"

    # -----------------------------
    # 4. Clean OCR text
    # -----------------------------
    cleaned_text = basic_clean(extracted_text)

    # -----------------------------
    # 5. Automatic Document Classifier
    # -----------------------------
    doc_type = classify_document(cleaned_text)

    # -----------------------------
    # 7. Create DB document row first so we have a document id for chunk global_ids
    # -----------------------------
    doc = OCRDocument(
        filename=file.filename,
        full_text=cleaned_text,
        pages=page_count,
        doc_type=doc_type,
    )

    db.add(doc)
    # flush to assign db-generated/default PK (UUID) without committing yet
    db.flush()

    # -----------------------------
    # 8. Chunk-level embeddings (now pass the doc id so global_id can include it)
    # -----------------------------
    embedded_chunks = embed_chunks(cleaned_text, doc_id=str(doc.id))

    # -----------------------------
    # 9. Full document embedding
    # -----------------------------
    full_embedding = embed_document_text(cleaned_text)

    # create chunks and link to doc (use correct column names)
    for c in embedded_chunks:
        chunk = ChunkModel(
            ocr_document_id=doc.id,
            chunk_id=c.get("chunk_id"),
            global_id=c.get("global_id"),
            text=c.get("text"),
            numbering=c.get("numbering"),
            embedding=c.get("embedding"),
        )
        db.add(chunk)

    # commit both document and chunks together
    db.commit()
    db.refresh(doc)

    # -----------------------------
    # 10. Remove temp file
    # -----------------------------
    try:
        os.remove(temp_path)
    except Exception as e:
        print(f"[WARN] Failed to remove temp file {temp_path}: {e}")

    # -----------------------------
    # 11. Return result
    # -----------------------------
    return {
        "doc_id": str(doc.id),
        "filename": file.filename,
        "pages": page_count,
        "doc_type": doc_type,
        "text": cleaned_text.strip(),
        "embedding_dim": len(full_embedding) if full_embedding else 0,
        "embedding": full_embedding,
        "chunks": embedded_chunks,
    }
