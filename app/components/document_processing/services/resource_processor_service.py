"""Service to process stored resources independently - OCR, chunking, and embedding."""

import os
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from sqlalchemy.orm import Session

from app.shared.models.resource_file import ResourceFile
from app.shared.models.resource_chunks import ResourceChunk

logger = logging.getLogger(__name__)


class ResourceProcessorService:
    """Process stored resources through OCR, chunking, and embedding pipeline."""

    def __init__(self, db: Session):
        self.db = db

    def _validate_resource_file(self, resource: ResourceFile):
        """Ensure resource file exists and is accessible."""
        if not resource.storage_path:
            raise ValueError("Resource has no storage path")
        
        if not os.path.exists(resource.storage_path):
            raise ValueError(f"Resource file not found: {resource.storage_path}")
        
        file_ext = Path(resource.storage_path).suffix.lower()
        if file_ext not in ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.webp']:
            raise ValueError(f"Unsupported file type: {file_ext}")

    def _extract_text(self, file_path: str) -> tuple[str, int]:
        """
        Extract text from PDF or image file.
        
        Returns:
            (extracted_text, page_count)
        """
        # Import OCR utilities directly
        from app.components.document_processing.utils.file_operations import convert_file_to_images
        from app.components.document_processing.services.text_extraction import process_ocr_for_images
        from app.components.document_processing.utils.text_cleaner import basic_clean
        
        file_ext = Path(file_path).suffix.lower()
        
        try:
            # Convert to images for OCR processing
            images = convert_file_to_images(file_path, file_ext.lstrip('.'))
            extracted_text, page_count = process_ocr_for_images(images)
            cleaned_text = basic_clean(extracted_text)
            
            return cleaned_text, page_count
        except Exception as e:
            logger.error(f"Failed to extract text from {file_path}: {e}")
            raise ValueError(f"Text extraction failed: {e}")

    def _create_chunks(self, text: str, resource_id: str) -> List[Dict[str, Any]]:
        """
        Split text into chunks and generate embeddings.
        
        Returns:
            List of chunk dictionaries with embeddings
        """
        from app.components.document_processing.services.embedding_service import embed_chunks
        
        try:
            embedded_chunks = embed_chunks(text, doc_id=resource_id)
            return embedded_chunks
        except Exception as e:
            logger.error(f"Failed to create chunks for resource {resource_id}: {e}")
            raise ValueError(f"Chunking failed: {e}")

    def _generate_pseudo_questions_for_chunk(self, text: str) -> str:
        sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 20]
        questions = []

        for s in sentences[:3]:
            questions.append(f"{s} යනු කුමක්ද?")
            questions.append(f"{s} ගැන පැහැදිලි කරන්න.")

        return "\n".join(questions[:5])

    def _save_chunks_to_db(self, chunks: List[Dict[str, Any]], resource_id: str):
        """Persist chunks with embeddings to database."""
        for chunk_data in chunks:
            content = chunk_data.get("text")
            chunk = ResourceChunk(
                resource_id=resource_id,
                chunk_index=chunk_data.get("chunk_id"),
                content=content,
                content_length=len(content) if content else None,
                token_count=None,
                embedding=chunk_data.get("embedding"),
                embedding_model=chunk_data.get("embedding_model"),
                start_char=chunk_data.get("start_char"),
                end_char=chunk_data.get("end_char"),
                pseudo_questions=(
                    self._generate_pseudo_questions_for_chunk(content)
                    if content else None
                ),
            )

            self.db.add(chunk)
        
        self.db.commit()
        logger.info("Saved %d chunks for resource %s", len(chunks), resource_id)

    def _create_document_embedding(self, text: str, resource_id: str) -> Optional[List[float]]:
        """Generate a document-level embedding for fast filtering."""
        from app.components.document_processing.services.embedding_service import embed_document_text
        
        try:
            embedding = embed_document_text(text)
            if embedding:
                logger.info("Generated document embedding for resource %s", resource_id)
            return embedding
        except Exception as e:
            logger.error(f"Failed to create document embedding for resource {resource_id}: {e}")
            return None
    
    def process_resource(
        self, 
        resource: ResourceFile, 
    ) -> Dict[str, Any]:
        """
        Process a stored resource: extract text, chunk, embed, and save.
        
        Args:
            resource: ResourceFile instance with storage_path
            doc_type: Optional document type (for metadata only)
            
        Returns:
            Processing results including extracted text and chunk count
            
        Raises:
            ValueError: If resource file is missing or processing fails
        """
        # Validate resource
        self._validate_resource_file(resource)
        
        logger.info("Starting processing for resource %s: %s", resource.id, resource.original_filename)
        
        # Extract text via OCR
        extracted_text, page_count = self._extract_text(resource.storage_path)
        
        if not extracted_text.strip():
            raise ValueError("No text could be extracted from the document")
        
        logger.info("Extracted %d characters from %d pages", len(extracted_text), page_count)
        
        # Generate document-level embedding (for fast filtering)
        from app.shared.ai.embeddings import EMBED_MODEL
        
        document_embedding = self._create_document_embedding(extracted_text, str(resource.id))
        if document_embedding:
            resource.document_embedding = document_embedding
            resource.embedding_model = EMBED_MODEL
            self.db.commit()

        # Create chunks with embeddings (for detailed retrieval)
        chunks = self._create_chunks(extracted_text, str(resource.id))
        
        # Save chunks to database
        self._save_chunks_to_db(chunks, str(resource.id))
        
        return {
            "resource_id": str(resource.id),
            "status": "completed",
            "pages": page_count,
            "extracted_text_length": len(extracted_text),
            "chunks_created": len(chunks),
            "message": "Resource processed successfully"
        }
