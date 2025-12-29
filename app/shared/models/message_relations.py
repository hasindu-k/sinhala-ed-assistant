import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Numeric, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class MessageContextChunk(Base):
    __tablename__ = "message_context_chunks"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False, index=True)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("resource_chunks.id"), nullable=False, index=True)
    similarity_score = Column(Numeric, nullable=True)
    rank = Column(Integer, nullable=True)

    message = relationship(
        "Message",
        back_populates="context_chunks"
    )


class MessageAttachment(Base):
    __tablename__ = "message_attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False, index=True)
    resource_id = Column(UUID(as_uuid=True), ForeignKey("resource_files.id"), nullable=False, index=True)
    display_name = Column(String, nullable=True)
    attachment_type = Column(String, nullable=True) # pdf, image, audio, doc
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    message = relationship(
        "Message",
        back_populates="attachments"
    )
    
    resource = relationship(
        "ResourceFile",
        foreign_keys=[resource_id]
    )



class MessageSafetyReport(Base):
    __tablename__ = "message_safety_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False, index=True)
    missing_concepts = Column(String, nullable=True)  # JSONB stored as string
    extra_concepts = Column(String, nullable=True)  # JSONB stored as string
    flagged_sentences = Column(String, nullable=True)  # JSONB stored as string
    reasoning = Column(String, nullable=True)  # JSONB stored as string
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    message = relationship(
        "Message",
        back_populates="safety_reports"
    )
