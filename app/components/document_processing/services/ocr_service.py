# app/components/document_processing/services/ocr_service.py

import logging

from app.components.document_processing.utils.file_operations import (
    convert_file_to_images
)
from app.components.document_processing.utils.text_cleaner import basic_clean
from app.components.document_processing.services.text_extraction import (
    extract_text_from_pdf,
    process_ocr_for_images_with_tables,
)

logger = logging.getLogger(__name__)

# Utility function
def extract_and_clean_text_from_file(file_path: str, force_layout_analysis: bool = True) -> tuple[str, int]:
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
            extracted_text, page_count = process_ocr_for_images_with_tables(images, force_layout_analysis)
            logger.info(f"OCR extracted text: {page_count} pages, {len(extracted_text)} characters")
        
        # Clean the extracted text
        cleaned_text = basic_clean(extracted_text)
        logger.info(f"Text cleaned: {len(cleaned_text)} characters after cleaning")
        
        return cleaned_text, page_count
        
    except Exception as e:
        logger.error(f"Error extracting text from file {file_path}: {e}", exc_info=True)
        raise ValueError(f"Failed to extract text from file: {e}")
