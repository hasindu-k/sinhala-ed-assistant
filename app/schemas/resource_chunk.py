# app/schemas/resource_chunk.py

from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID


class ResourceChunkCreate(BaseModel):
    resource_id: UUID
    chunk_index: Optional[int] = None
    content: str
    content_length: Optional[int] = None
    token_count: Optional[int] = None
    embedding: Optional[List[float]] = None
    embedding_model: Optional[str] = None
    start_char: Optional[int] = None
    end_char: Optional[int] = None


class ResourceChunkUpdate(BaseModel):
    content: Optional[str] = None
    embedding: Optional[List[float]] = None
    embedding_model: Optional[str] = None


class ResourceChunkResponse(BaseModel):
    id: UUID
    resource_id: UUID
    chunk_index: Optional[int]
    content: str
    content_length: Optional[int]
    token_count: Optional[int]
    embedding: Optional[List[float]]
    embedding_model: Optional[str]
    start_char: Optional[int]
    end_char: Optional[int]

    class Config:
        from_attributes = True
