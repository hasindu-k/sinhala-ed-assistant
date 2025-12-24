# scripts/migrate_chunks.py
import sys
import os
import uuid
from sqlalchemy.orm import Session

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, engine, Base
from app.shared.models.text_chunk import TextChunk
from app.shared.models.resource_data import ResourceData
from app.components.text_qa_summary.services.chunking_service import ChunkingService
from app.components.text_qa_summary.services.embedding_service import EmbeddingService
from app.core.config import settings


def migrate_existing_resources():
    """Migrate existing resources to chunks"""
    db = SessionLocal()
    try:
        print("=" * 60)
        print("STARTING MIGRATION: Processing existing resources into chunks")
        print("=" * 60)
        
        # Create tables if not exist
        print("Creating database tables if they don't exist...")
        Base.metadata.create_all(bind=engine)
        
        # Get all resources
        resources = db.query(ResourceData).all()
        
        print(f"Found {len(resources)} resources to migrate")
        
        migrated_count = 0
        error_count = 0
        
        for i, resource in enumerate(resources, 1):
            print(f"\n[{i}/{len(resources)}] Processing resource {resource.id}")
            print(f"  Chat: {resource.chat_id}, User: {resource.user_id}")
            print(f"  Text length: {len(resource.resource_text)} characters")
            
            # Check if already chunked
            existing_chunks = db.query(TextChunk).filter(
                TextChunk.resource_id == resource.id
            ).count()
            
            if existing_chunks > 0:
                print(f"  ✓ Already has {existing_chunks} chunks, skipping")
                continue
            
            try:
                # Process resource into chunks
                print(f"  Splitting resource into chunks...")
                chunks = ChunkingService.process_resource(
                    db, resource.id, resource.chat_id, resource.user_id
                )
                
                print(f"  Created {len(chunks)} chunks, generating embeddings...")
                
                # Generate embeddings
                chunk_contents = [chunk.content for chunk in chunks]
                embeddings = EmbeddingService.get_embeddings(chunk_contents)
                
                # Update chunks with embeddings
                for chunk, embedding in zip(chunks, embeddings):
                    chunk.embedding = embedding
                    chunk.embedding_model = settings.MODEL_EMBEDDING_NAME
                
                db.commit()
                print(f"  ✓ Successfully created {len(chunks)} chunks with embeddings")
                migrated_count += 1
                
            except Exception as e:
                print(f"  ✗ Error processing resource: {str(e)}")
                import traceback
                traceback.print_exc()
                db.rollback()
                error_count += 1
        
        print("\n" + "=" * 60)
        print("MIGRATION COMPLETE!")
        print(f"Successfully migrated: {migrated_count} resources")
        print(f"Errors: {error_count}")
        print(f"Skipped (already chunked): {len(resources) - migrated_count - error_count}")
        print("=" * 60)
        
    finally:
        db.close()


if __name__ == "__main__":
    migrate_existing_resources()