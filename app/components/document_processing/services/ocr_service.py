# app/components/document_processing/services/ocr_service.py

import logging
from typing import Optional

from fastapi import UploadFile, Depends

from sqlalchemy.orm import Session
from app.shared.models.resource_file import ResourceFile
from app.shared.models.resource_chunks import ResourceChunk
from app.core.database import get_db
from app.components.document_processing.utils.file_operations import (
    save_upload_to_temp, 
    remove_temp_file, 
    convert_file_to_images
)
from app.components.document_processing.utils.text_cleaner import basic_clean
from app.components.document_processing.services.embedding_service import (
    embed_chunks,
    embed_document_text,
)
from app.components.document_processing.services.classifier_service import separate_paper_content
from app.components.document_processing.services.text_extraction import (
    extract_text_from_pdf,
    process_ocr_for_images,
)
from app.components.document_processing.utils.pdf_analysis import (
    check_for_images_in_pdf,
    check_for_tables_in_pdf,
    should_use_direct_text_extraction,
)

logger = logging.getLogger(__name__)

# Utility function
def extract_and_clean_text_from_file(file_path: str) -> tuple[str, int]:
    """
    Extract text from a file (PDF or image) and return cleaned text with page count.
    
    Args:
        file_path: Full path to the file
        
    Returns:
        Tuple of (cleaned_text, page_count)
        
    Raises:
        ValueError: If file cannot be processed
    """
    try:
        # Get file extension
        ext = file_path.split(".")[-1].lower() if "." in file_path else ""
        
        extracted_text = None
        page_count = 0
        
        # Try direct PDF text extraction if applicable
        if ext == "pdf":
            try:
                extracted_text, page_count = extract_text_from_pdf(file_path)
                logger.info(f"Extracted text directly from PDF: {page_count} pages")
                # check if text is sufficient for page count
                if len(extracted_text.strip()) < 100 * page_count:
                    logger.info("Extracted text seems insufficient, falling back to OCR.")
                    extracted_text = None  # trigger OCR fallback
            except Exception as e:
                logger.warning(f"Direct PDF extraction failed, falling back to OCR: {e}")
                extracted_text = None
        
        # Fall back to OCR if needed
        if extracted_text is None:
            logger.info(f"Starting OCR for file: {file_path}")
            images = convert_file_to_images(file_path, ext)
            extracted_text, page_count = process_ocr_for_images(images)
            logger.info(f"OCR extracted text: {page_count} pages, {len(extracted_text)} characters")
        
        # Clean the extracted text
        cleaned_text = basic_clean(extracted_text)
        logger.info(f"Text cleaned: {len(cleaned_text)} characters after cleaning")
        
        return cleaned_text, page_count
        
    except Exception as e:
        logger.error(f"Error extracting text from file {file_path}: {e}", exc_info=True)
        raise ValueError(f"Failed to extract text from file: {e}")

# helper functions
async def save_ocr_document_to_db(
    file: UploadFile,
    cleaned_text: str,
    page_count: int,
    doc_type: str,
    db: Session,
    storage_path: Optional[str] = None,
    source_type: str = "user_upload",
) -> ResourceFile:
    """Persist the uploaded document as a ResourceFile entry."""
    doc = ResourceFile(
        original_filename=file.filename,
        storage_path=storage_path,
        mime_type=getattr(file, "content_type", None),
        size_bytes=None,
        source_type=source_type,
        language=None,
        user_id=None,
    )
    db.add(doc)
    db.flush()  # assign UUID
    db.commit()
    db.refresh(doc)
    return doc


async def save_chunks_to_db(embedded_chunks: list, resource_id: str, db: Session):
    """Persist chunk data into resource_chunks aligned with current schema."""
    for c in embedded_chunks:
        content = c.get("text")
        chunk = ResourceChunk(
            resource_id=resource_id,
            chunk_index=c.get("chunk_id"),
            content=content,
            content_length=len(content) if content else None,
            token_count=None,
            embedding=c.get("embedding"),
            embedding_model=c.get("embedding_model"),
            start_char=c.get("start_char"),
            end_char=c.get("end_char"),
        )
        db.add(chunk)

    db.commit()

async def save_processed_data_to_db(
    file: UploadFile,
    db: Session,
    doc_type: str,
    page_count: int,
    extracted_text: str,
    contains_images: bool,
    contains_tables: bool,
    storage_path: Optional[str] = None,
) -> ResourceFile:
    """Save processed document metadata into resource_files (single row)."""
    processed_doc = ResourceFile(
        original_filename=file.filename,
        storage_path=storage_path,
        mime_type=getattr(file, "content_type", None),
        size_bytes=None,
        source_type="user_upload",
        language=None,
        user_id=None,
    )
    db.add(processed_doc)
    db.commit()
    db.refresh(processed_doc)

    logger.info("Document %s saved successfully.", processed_doc.id)
    return processed_doc

# Main processing function
async def process_question_papers(file: UploadFile, db: Session = Depends(get_db)) -> dict:
    """
    Specialized OCR processing for exam question papers.
    Steps:
    1. Save file
    2. Convert PDF → Images if needed
    3. Check whether the document is text-based or scanned
    4. Check if the document contains images/diagrams
    5. Check if the document contains tables
    6. Extract text using OCR (if scanned)
    7. Classify the document (e.g., exam type, section headers, etc.)
    8. Insert processed data into the database
    """

    ext = file.filename.split(".")[-1].lower()
    if ext not in ["pdf", "png", "jpg", "jpeg", "tiff", "webp"]:
        logger.error("Unsupported file type received: %s", ext)
        raise ValueError("Unsupported file type. Please upload a PDF or image file.")

    # only papers
    doc_type = "exam_paper"

    # Step 1: Save file
    saved_file_path = await save_upload_to_temp(file)

    logger.info("Started processing question paper: %s", file.filename)
    
    # Step 3: Check if the document is text-based or scanned
    is_text_based_file = should_use_direct_text_extraction(saved_file_path)

    if is_text_based_file:
        extracted_text, page_count = extract_text_from_pdf(saved_file_path)
    else:
        images = convert_file_to_images(saved_file_path, ext)
        extracted_text, page_count = process_ocr_for_images(images)

    # Step 4: Check if the document contains images/diagrams
    contains_images = check_for_images_in_pdf(saved_file_path, is_scanned=not is_text_based_file)
    
    # Step 5: Check if the document contains tables
    contains_tables = check_for_tables_in_pdf(saved_file_path, is_scanned=not is_text_based_file)

    # Step 6: Perform additional processing or classification if necessary (optional)
    cleaned_text = basic_clean(extracted_text)
    # separate  paper metadata, instructions, and question sections using generative AI if needed
    paper_metadata, instructions, paper_structure = separate_paper_content(cleaned_text)

    logger.debug("Paper metadata: %s", paper_metadata)
    logger.debug("Instructions: %s", instructions)
    logger.debug("Paper structure: %s", paper_structure)

    # Step 7: Insert the processed data into the database
    logger.info("Inserting processed data into the database...")
    logger.debug("Extracted Text: %s", cleaned_text)
    logger.debug("Contains Images: %s", contains_images)
    logger.debug("Contains Tables: %s", contains_tables)

    # Call save_processed_data_to_db to insert data into the database
    resource = await save_processed_data_to_db(
        file=file,
        db=db,
        doc_type=doc_type,
        page_count=page_count,
        extracted_text=cleaned_text,
        contains_images=contains_images,
        contains_tables=contains_tables,
        storage_path=saved_file_path,
    )

    return {
        "status": "success",
        "doc_type": doc_type,
        "extracted_text": cleaned_text,
        "contains_images": contains_images,
        "contains_tables": contains_tables,
        "paper_metadata": paper_metadata,
        "instructions": instructions,
        "paper_structure": paper_structure,
        "resource_id": str(resource.id),
    }


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
    images = convert_file_to_images(temp_path, ext)

    extracted_text, page_count = process_ocr_for_images(images)

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
    doc = await save_ocr_document_to_db(
        file=file,
        cleaned_text=cleaned_text,
        page_count=page_count,
        doc_type=doc_type,
        db=db,
        storage_path=temp_path,
    )

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

async def process_syllabus_files(file: UploadFile, db: Session = Depends(get_db)) -> dict:
    """
    OCR processing for syllabus documents.
    Similar to process_ocr_file but tailored for syllabus documents.
    """
    # -----------------------------
    # 1. Save uploaded file temporarily
    # -----------------------------
    temp_path = await save_upload_to_temp(file)
    ext = file.filename.split(".")[-1].lower()

    # -----------------------------
    # 2. Detect PDF or Image
    # -----------------------------
    images = convert_file_to_images(temp_path, ext)

    extracted_text, page_count = process_ocr_for_images(images)

    # -----------------------------
    # 4. Clean OCR text
    # -----------------------------
    cleaned_text = basic_clean(extracted_text)

    # -----------------------------
    # 5. Document type is syllabus
    # -----------------------------
    doc_type = "syllabus"

    # -----------------------------
    # 7. Create DB document row first so we have a document id for chunk global_ids
    # -----------------------------
    doc = await save_ocr_document_to_db(
        file=file,
        cleaned_text=cleaned_text,
        page_count=page_count,
        doc_type=doc_type,
        db=db,
        storage_path=temp_path,
    )

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


async def process_textbooks(file: UploadFile, db: Session = Depends(get_db)) -> dict:
    """
    OCR processing for textbooks.
    Steps:
    1. Save file
    2. Detect PDF / Image
    3. Detect text-based vs scanned
    4. Extract text (direct or OCR)
    5. Clean text
    6. Create DB document
    7. Chunk + embed
    8. Save chunks
    9. Full document embedding
    """

    # -----------------------------
    # 1. Validate file
    # -----------------------------
    ext = file.filename.split(".")[-1].lower()
    if ext not in {"pdf", "png", "jpg", "jpeg", "tiff", "webp"}:
        raise ValueError("Unsupported file type")

    doc_type = "textbook"

    # -----------------------------
    # 2. Save uploaded file
    # -----------------------------
    temp_path = await save_upload_to_temp(file)

    # -----------------------------
    # 3. Extract text (hybrid logic)
    # -----------------------------
    # if ext == "pdf" and should_use_direct_text_extraction(temp_path):
    #     extracted_text, page_count = extract_text_from_pdf(temp_path)

    #     if looks_like_legacy_sinhala(extracted_text):
    #         print("⚠ Legacy Sinhala detected → switching to OCR")
    #         images = convert_file_to_images(temp_path, ext)
    #         extracted_text, page_count = await process_ocr_for_images(images)
    # else:
    images = convert_file_to_images(temp_path, ext)
    extracted_text, page_count = process_ocr_for_images(images)

    # -----------------------------
    # 4. Clean text
    # -----------------------------
    cleaned_text = basic_clean(extracted_text)

    if not cleaned_text.strip():
        raise ValueError("No readable text found in document")

    # -----------------------------
    # 5. Create document DB row first
    # -----------------------------
    doc = await save_ocr_document_to_db(
        file=file,
        cleaned_text=cleaned_text,
        page_count=page_count,
        doc_type=doc_type,
        db=db,
        storage_path=temp_path,
    )

    # -----------------------------
    # 6. Chunk + embed (chunk-level)
    # -----------------------------
    embedded_chunks = embed_chunks(
        cleaned_text,
        doc_id=str(doc.id)
    )

    await save_chunks_to_db(
        embedded_chunks=embedded_chunks,
        resource_id=doc.id,
        db=db,
    )

    # -----------------------------
    # 7. Full-document embedding
    # -----------------------------
    full_embedding = embed_document_text(cleaned_text)

    # -----------------------------
    # 8. Cleanup
    # -----------------------------
    await remove_temp_file(temp_path)

    # -----------------------------
    # 9. Return response
    # -----------------------------
    return {
        "status": "success",
        "doc_id": str(doc.id),
        "filename": file.filename,
        "doc_type": doc_type,
        "pages": page_count,
        "embedding_dim": len(full_embedding) if full_embedding else 0,
        "chunks": embedded_chunks,
    }
