import re
from typing import List


def split_extracted_text_pages(extracted_text: str) -> List[str]:
    """Split OCR text by page markers while preserving marker headers."""
    if not extracted_text:
        return []

    pages = [
        page.strip()
        for page in re.split(r"(?=\s*---\s*PAGE\s+\d+\s*---)", extracted_text)
        if page.strip()
    ]
    return pages or [extracted_text.strip()]
