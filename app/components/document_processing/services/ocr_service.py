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
    images = await convert_file_to_images(temp_path, ext)

    extracted_text, page_count = await process_images_for_ocr(images)

    # -----------------------------
    # 4. Clean OCR text
    # -----------------------------
    cleaned_text = basic_clean(extracted_text)

    # -----------------------------
    # 5. Automatic Document Classifier
    # -----------------------------
    # doc_type = classify_document(cleaned_text)
    doc_type = "past_paper"

    # -----------------------------
    # 7. Create DB document row first so we have a document id for chunk global_ids
    # -----------------------------
    doc = await save_ocr_document_to_db(file, cleaned_text, page_count, doc_type, db)

    # -----------------------------
    # 8. Chunk-level embeddings (now pass the doc id so global_id can include it)
    # -----------------------------
    embedded_chunks = embed_chunks(cleaned_text, doc_id=str(doc.id))

    # -----------------------------
    # 9. Full document embedding
    # -----------------------------
    full_embedding = embed_document_text(cleaned_text)

    # create chunks and link to doc (use correct column names)
    await save_chunks_to_db(embedded_chunks, doc.id, db)

    # -----------------------------
    # 10. Remove temp file
    # -----------------------------
    await remove_temp_file(temp_path)

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


async def convert_file_to_images(file_path: str, file_extension: str) -> list:
    """
    Convert PDF to images, or return image for other file types.
    """
    if file_extension == "pdf":
        return convert_from_path(file_path)
    else:
        return [Image.open(file_path)]


async def process_images_for_ocr(images: list) -> tuple:
    """
    Perform OCR processing on a list of images.
    """
    extracted_text = ""
    page_count = 0

    for pil_img in images:
        page_count += 1
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        processed = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        tess_config = (
            "--oem 1 "
            "--psm 6 "
            "-c preserve_interword_spaces=1 "
        )

        text = pytesseract.image_to_string(
            processed, lang="sin+eng", config=tess_config
        )

        extracted_text += f"\n\n--- PAGE {page_count} ---\n{text}"

    return extracted_text, page_count


async def save_ocr_document_to_db(file: UploadFile, cleaned_text: str, page_count: int, doc_type: str, db: Session) -> OCRDocument:
    """
    Save the OCR document details to the database.
    """
    doc = OCRDocument(
        filename=file.filename,
        full_text=cleaned_text,
        pages=page_count,
        doc_type=doc_type,
    )
    db.add(doc)
    db.flush()  # flush to assign db-generated/default PK (UUID)
    db.commit()
    db.refresh(doc)

    return doc


async def save_chunks_to_db(embedded_chunks: list, doc_id: str, db: Session):
    """
    Save the chunk data into the database.
    """
    for c in embedded_chunks:
        chunk = ChunkModel(
            ocr_document_id=doc_id,
            chunk_id=c.get("chunk_id"),
            global_id=c.get("global_id"),
            text=c.get("text"),
            numbering=c.get("numbering"),
            embedding=c.get("embedding"),
        )
        db.add(chunk)

    db.commit()


async def remove_temp_file(temp_path: str):
    """
    Remove the temporary file after processing.
    """
    try:
        os.remove(temp_path)
    except Exception as e:
        print(f"[WARN] Failed to remove temp file {temp_path}: {e}")
