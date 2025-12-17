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
from app.components.document_processing.utils.text_cleaner import basic_clean, looks_like_legacy_sinhala
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

async def save_processed_data_to_db(file: UploadFile, db: Session, doc_type: str, page_count: int, extracted_text: str, contains_images: bool, contains_tables: bool):
    """
    Save the processed data (text, images, tables metadata) into the database.
    """
    processed_doc = OCRDocument(
        filename=file.filename,
        doc_type=doc_type,
        pages=page_count,
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

    ext = file.filename.split(".")[-1].lower()
    if ext not in ["pdf", "png", "jpg", "jpeg", "tiff", "webp"]:
        raise ValueError("Unsupported file type. Please upload a PDF or image file.")

    # only papers
    doc_type = "exam_paper"

    # Step 1: Save file
    saved_file_path = await save_upload_to_temp(file)
    
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

    print(f"Paper Metadata: {paper_metadata}")
    print(f"Instructions: {instructions}")
    print(f"Paper Structure: {paper_structure}")

    # Step 7: Insert the processed data into the database
    print("Inserting processed data into the database...")
    print(f"Extracted Text: {cleaned_text}")
    print(f"Contains Images: {contains_images}")
    print(f"Contains Tables: {contains_tables}")

    # Call save_processed_data_to_db to insert data into the database
    await save_processed_data_to_db(file, db, doc_type, page_count, cleaned_text, contains_images, contains_tables)

    return {
        "status": "success",
        "doc_type": doc_type,
        "extracted_text": cleaned_text,
        "contains_images": contains_images,
        "contains_tables": contains_tables,
        "paper_metadata": paper_metadata,
        "instructions": instructions,
        "paper_structure": paper_structure,
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
        db=db
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
        doc_id=doc.id,
        db=db
    )

    # -----------------------------
    # 7. Full-document embedding
    # -----------------------------
    full_embedding = embed_document_text(cleaned_text)

    # -----------------------------
    # 8. Cleanup
    # -----------------------------
    remove_temp_file(temp_path)

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
