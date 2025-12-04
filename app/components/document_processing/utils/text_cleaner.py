# app/components/document_processing/utils/text_cleaner.py

import re

def basic_clean(text: str) -> str:
    """
    Very simple text cleaner.
    TODO: Improve for Sinhala script normalization.
    """
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text
