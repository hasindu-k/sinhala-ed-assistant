# app/models/document.py

from typing import List, Optional
from beanie import Document
from pydantic import BaseModel, Field
from datetime import datetime


# -------------------------------
# Chunk Schema
# -------------------------------
class Chunk(BaseModel):
    chunk_id: int
    global_id: str           # <doc_id>_<chunk_id>
    text: str
    numbering: Optional[str] = None  # 1, 1.1, Q1(a), අ), etc.
    embedding: List[float]


# -------------------------------
# Main OCR Document Schema
# -------------------------------
class OCRDocument(Document):
    filename: str
    full_text: str
    pages: int

    # classification result (teacher guide / term test / notes / etc.)
    doc_type: str

    # all embedded + numbered chunks
    chunks: List[Chunk]

    # optional future metadata
    subject: Optional[str] = None       # auto-extraction coming later
    grade: Optional[str] = None
    year: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "ocr_documents"   # MongoDB collection name
