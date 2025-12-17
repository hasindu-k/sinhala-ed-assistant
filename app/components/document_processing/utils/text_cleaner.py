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
    print(f"Original text before removing weird chars: {text}")
    # allowed = r"[^\u0D80-\u0DFFa-zA-Z0-9\s\.\-\(\)\[\]\/:;]"
    allowed = r"[^\u0D80-\u0DFF\u200D\u200Ca-zA-Z0-9\s\.\-\(\)\[\]\/:;]"
    text = re.sub(allowed, " ", text)
    print(f"Text after removing weird chars: {text}")
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
    print(f"Cleaned text: {text}")

    return text

def rule_based_correction(text: str) -> str:
    rules = {
        r"\bwa\b": "සහ",
        r"\bA\s*wa\b": "A සහ",
        # r"\b0\b": "D",
        # r"\b13\b": "E",
        # r"\b10\b": "E",
        # r"\bl\b": "C",
    }

    for pattern, replacement in rules.items():
        text = re.sub(pattern, replacement, text)

    return text

def looks_like_legacy_sinhala(text: str) -> bool:
    # Sinhala Unicode range: \u0D80 – \u0DFF
    sinhala_unicode = re.search(r'[\u0D80-\u0DFF]', text)
    ascii_heavy = re.search(r'[a-zA-Z;=<>]', text)

    return (not sinhala_unicode) and ascii_heavy