# app/components/document_processing/utils/text_cleaner.py

import re
import unicodedata
import logging
logger = logging.getLogger(__name__)

def normalize_sinhala(text: str) -> str:
    """
    Normalize Sinhala Unicode to avoid duplicated diacritics,
    OCR glitches, or mixed normalization forms.
    """
    return unicodedata.normalize("NFC", text)


def remove_weird_chars(text: str) -> str:
    """
    Remove garbage but keep Sinhala + English + numbers + numbering symbols.
    """
    logger.debug("Original text before removing weird chars: %s", text)
    allowed = r"[^\u0D80-\u0DFF\u200D\u200Ca-zA-Z0-9\s\.\-\(\)\[\]\/:;]"
    text = re.sub(allowed, " ", text)
    logger.debug("Text after removing weird chars: %s", text)
    return text


def basic_clean(text: str) -> str:
    """
    Basic cleaning pipeline for Sinhala OCR text.
    Removes noise but keeps meaning safe.
    """

    if not text:
        return ""

    # Step 1: Unicode normalization (critical for Sinhala)
    text = normalize_sinhala(text)

    # Step 2: Remove strange OCR characters
    text = remove_weird_chars(text)

    # Step 3: Replace multiple spaces with single space
    text = re.sub(r"\s+", " ", text)

    # Step 4: Trim
    text = text.strip()

    text = rule_based_correction(text)
    
    # log cleaned text
    logger.debug("Cleaned text: %s", text)
    logger.info("Text cleaned successfully.")

    return text

def rule_based_correction(text: str) -> str:
    rules = {
        r"\bwa\b": "සහ",
        r"\bA\s*wa\b": "A සහ",
    }

    for pattern, replacement in rules.items():
        text = re.sub(pattern, replacement, text)

    return text
