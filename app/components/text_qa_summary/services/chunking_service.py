import re
import uuid
from typing import List
from sqlalchemy.orm import Session

from app.shared.models.resource_data import ResourceData
from app.shared.models.text_chunk import TextChunk
from app.components.text_qa_summary.utils.sinhala_processor import (
    tokenize_sinhala,
    extract_lesson_numbers,
    extract_key_phrases
)


class ChunkingService:
    @staticmethod
    def split_by_paragraphs(text: str, min_chunk_size: int = 100, max_chunk_size: int = 500) -> List[str]:
        """
        Split Sinhala text into paragraphs/chunks
        """
        if not text or len(text.strip()) == 0:
            return []
            
        # Split by common Sinhala paragraph boundaries
        paragraphs = re.split(r'[\n]{2,}|\.\s+(?=[අ-෴])', text)
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para or len(para) < 20:
                continue
                
            para_length = len(para)
            
            # If paragraph is very large, split further
            if para_length > max_chunk_size:
                sentences = re.split(r'[.!?]+\s+', para)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence or len(sentence) < 10:
                        continue
                        
                    sentence_length = len(sentence)
                    if current_size + sentence_length > max_chunk_size and current_size >= min_chunk_size:
                        chunks.append(' '.join(current_chunk))
                        current_chunk = [sentence]
                        current_size = sentence_length
                    else:
                        current_chunk.append(sentence)
                        current_size += sentence_length
            else:
                if current_size + para_length > max_chunk_size and current_size >= min_chunk_size:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = [para]
                    current_size = para_length
                else:
                    current_chunk.append(para)
                    current_size += para_length
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    @staticmethod
    def process_resource(
        db: Session, 
        resource_id: uuid.UUID,
        chat_id: uuid.UUID,
        user_id: str
    ) -> List[TextChunk]:
        """
        Process a resource: split into chunks, tokenize, and index
        """
        # Get the resource
        resource = db.query(ResourceData).filter(ResourceData.id == resource_id).first()
        if not resource:
            raise ValueError(f"Resource {resource_id} not found")
        
        # Check if resource has text
        if not resource.resource_text or len(resource.resource_text.strip()) == 0:
            raise ValueError(f"Resource {resource_id} has no text content")
        
        # Delete existing chunks for this resource
        db.query(TextChunk).filter(TextChunk.resource_id == resource_id).delete()
        
        # Split into chunks
        chunks = ChunkingService.split_by_paragraphs(resource.resource_text)
        
        if not chunks:
            # If no chunks were created, create at least one chunk with the full text
            chunks = [resource.resource_text[:max_chunk_size]]
        
        # Create chunk records
        chunk_objects = []
        for i, chunk_content in enumerate(chunks):
            # Tokenize for BM25
            tokens = tokenize_sinhala(chunk_content)
            
            # Extract metadata
            lesson_numbers = extract_lesson_numbers(chunk_content)
            key_phrases = extract_key_phrases(chunk_content)
            
            # Create chunk object (embedding will be added later)
            chunk = TextChunk(
                id=uuid.uuid4(),
                resource_id=resource_id,
                chat_id=chat_id,
                user_id=user_id,
                chunk_index=i,
                content=chunk_content,
                content_length=len(chunk_content),
                tokens=tokens,
                lesson_numbers=lesson_numbers,
                key_phrases=key_phrases
            )
            
            chunk_objects.append(chunk)
            db.add(chunk)
        
        db.commit()
        
        return chunk_objects
    
    @staticmethod
    def get_resource_chunks(db: Session, resource_id: uuid.UUID) -> List[TextChunk]:
        """
        Get all chunks for a resource
        """
        return db.query(TextChunk).filter(
            TextChunk.resource_id == resource_id
        ).order_by(TextChunk.chunk_index).all()
    
    @staticmethod
    def get_chat_chunks(db: Session, chat_id: uuid.UUID) -> List[TextChunk]:
        """
        Get all chunks for a chat
        """
        return db.query(TextChunk).filter(
            TextChunk.chat_id == chat_id
        ).order_by(TextChunk.created_at).all()
    
    @staticmethod
    def count_chat_chunks(db: Session, chat_id: uuid.UUID) -> int:
        """
        Count all chunks for a chat
        """
        return db.query(TextChunk).filter(
            TextChunk.chat_id == chat_id
        ).count()