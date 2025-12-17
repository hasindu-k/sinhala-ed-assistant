# app/database/models.py

import uuid
from sqlalchemy import Boolean, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from pgvector.sqlalchemy import Vector

from app.core.database import Base


class OCRDocument(Base):
    __tablename__ = "ocr_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String, nullable=False)
    full_text = Column(Text, nullable=False)
    pages = Column(Integer, nullable=False)
    doc_type = Column(String, nullable=False)

    subject = Column(String, nullable=True)
    grade = Column(String, nullable=True)
    year = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    contains_images = Column(Boolean, default=False)
    contains_tables = Column(Boolean, default=False)


    # relationship to chunks
    chunks = relationship("ChunkModel", back_populates="document", cascade="all, delete")


class ChunkModel(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True)
    ocr_document_id = Column(UUID(as_uuid=True), ForeignKey("ocr_documents.id"))
    chunk_id = Column(Integer)
    global_id = Column(String)
    text = Column(Text)
    numbering = Column(String, nullable=True)

    # embedding vector (example: 768 dimensions)
    embedding = Column(Vector(768))

    document = relationship("OCRDocument", back_populates="chunks")
