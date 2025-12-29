
import uuid
from sqlalchemy import Column, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.core.database import Base

class UserEvaluationContext(Base):
    __tablename__ = "user_evaluation_contexts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    active_syllabus_id = Column(UUID(as_uuid=True), ForeignKey("resource_files.id"), nullable=True)
    active_question_paper_id = Column(UUID(as_uuid=True), ForeignKey("resource_files.id"), nullable=True)
    active_rubric_id = Column(UUID(as_uuid=True), ForeignKey("rubrics.id"), nullable=True)
    
    # Stores the configuration (weightage, parts, etc.) for the active question paper
    active_paper_config = Column(JSONB, nullable=True)
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
