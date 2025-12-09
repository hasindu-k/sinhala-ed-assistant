# app/components/document_processing/services/ocr_service.py

from fastapi import UploadFile, Depends

from sqlalchemy.orm import Session
from app.database.models import OCRDocument, ChunkModel
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
from app.components.document_processing.services.classifier_service import classify_document
from app.components.document_processing.services.text_extraction import (
    extract_text_from_pdf,
    process_ocr_for_images,
)
from app.components.document_processing.utils.pdf_analysis import (
    check_for_images_in_pdf,
    check_for_tables_in_pdf,
    is_text_based,
)

# helper functions
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

async def save_processed_data_to_db(db: Session, doc_type: str, extracted_text: str, contains_images: bool, contains_tables: bool):
    """
    Save the processed data (text, images, tables metadata) into the database.
    """
    processed_doc = OCRDocument(
        doc_type=doc_type,
        full_text=extracted_text,
        contains_images=contains_images,
        contains_tables=contains_tables,
    )
    db.add(processed_doc)
    db.commit()
    db.refresh(processed_doc)

    print(f"Document {processed_doc.id} saved successfully.")

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

    # only papers
    doc_type = "exam_paper"

    # Step 1: Save file
    saved_file_path = await save_upload_to_temp(file)
    
    # Step 3: Check if the document is text-based or scanned
    is_text_based_file = is_text_based(saved_file_path)
    if is_text_based_file:
        # Process as text-based (e.g., extract text directly)
        extracted_text = extract_text_from_pdf(saved_file_path)
    else:
        ext = file.filename.split(".")[-1].lower()
        images = convert_file_to_images(saved_file_path, ext)
        extracted_text = process_ocr_for_images(images)

    # Step 4: Check if the document contains images/diagrams
    contains_images = check_for_images_in_pdf(saved_file_path, is_scanned=not is_text_based_file)
    
    # Step 5: Check if the document contains tables
    contains_tables = check_for_tables_in_pdf(saved_file_path, is_scanned=not is_text_based_file)

    # Step 6: Perform additional processing or classification if necessary (optional)

    # Step 7: Insert the processed data into the database
    print("Inserting processed data into the database...")
    print(f"Extracted Text: {extracted_text}")
    print(f"Contains Images: {contains_images}")
    print(f"Contains Tables: {contains_tables}")

    # Call save_processed_data_to_db to insert data into the database
    await save_processed_data_to_db(db, doc_type, extracted_text, contains_images, contains_tables)

    return {
        "status": "success",
        "doc_type": doc_type,
        "extracted_text": extracted_text,
        "contains_images": contains_images,
        "contains_tables": contains_tables,
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

    extracted_text, page_count = await process_ocr_for_images(images)

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

