# app/components/document_processing/utils/text_cleaner.py

import re
import unicodedata

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
    allowed = r"[^\u0D80-\u0DFFa-zA-Z0-9\s\.\-\(\)\[\]\/:;]"
    text = re.sub(allowed, " ", text)
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
    
    # log cleaned text
    print(f"Cleaned text: {text}")

    return text
