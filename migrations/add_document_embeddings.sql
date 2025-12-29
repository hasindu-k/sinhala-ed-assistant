-- Migration: Add document-level embeddings to resource_files table
-- This enables two-stage retrieval: first filter by document, then search chunks

-- Add document embedding column (768 dimensions for text-embedding-004)
ALTER TABLE resource_files 
ADD COLUMN document_embedding vector(768);

-- Add embedding model column to track which model was used
ALTER TABLE resource_files 
ADD COLUMN embedding_model varchar;

-- Create index for fast document-level vector search
CREATE INDEX IF NOT EXISTS idx_resource_files_doc_embedding 
ON resource_files USING ivfflat (document_embedding vector_cosine_ops)
WITH (lists = 100);

-- Add comment for documentation
COMMENT ON COLUMN resource_files.document_embedding IS 'Full document embedding for fast filtering in two-stage retrieval';
COMMENT ON COLUMN resource_files.embedding_model IS 'Embedding model used (e.g., text-embedding-004)';
