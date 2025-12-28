CREATE INDEX IF NOT EXISTS idx_resource_chunks_embedding
ON resource_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

ANALYZE resource_chunks;