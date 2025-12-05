from beanie import Document
from typing import List

class OCRDocument(Document):
    filename: str
    full_text: str
    pages: int
    chunks: List[dict]  # [{"chunk_id": 0, "text": "...", "embedding": [...]}]

    class Settings:
        name = "ocr_documents"
