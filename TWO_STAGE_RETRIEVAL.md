# Two-Stage Retrieval Implementation

## Overview

This implementation adds **two-stage retrieval** to improve both speed and accuracy:

1. **Stage 1: Document Filtering** - Find top-N relevant documents using document embeddings (fast)
2. **Stage 2: Chunk Retrieval** - Search chunks only within those top documents (focused)

## Architecture

```
Query → Document Embedding Search → Top N Docs → Chunk Search → Results
         (Fast: O(documents))                     (Focused: O(chunks in N docs))
```

## Database Schema Changes

### New Fields in `resource_files`:

- `document_embedding`: `vector(768)` - Full document embedding for filtering
- `embedding_model`: `varchar` - Model used (e.g., "text-embedding-004")

### Migration:

```bash
psql -U your_user -d your_database -f migrations/add_document_embeddings.sql
```

## How It Works

### 1. Document Processing (Automatic)

When a resource is processed:

```python
# resource_processor_service.py
# 1. Extract text via OCR
extracted_text, page_count = self._extract_text(resource.storage_path)

# 2. Generate document-level embedding
document_embedding = embed_document_text(extracted_text)
resource.document_embedding = document_embedding
resource.embedding_model = EMBED_MODEL

# 3. Create chunk embeddings
chunks = self._create_chunks(extracted_text, str(resource.id))
self._save_chunks_to_db(chunks, str(resource.id))
```

### 2. Retrieval Flow (Automatic in RAG Service)

```python
# rag_service.py - Two-stage retrieval
def generate_response(
    session_id,
    user_message_id,
    user_query,
    resource_ids,
    query_embedding,
    top_k=8,          # Chunks to retrieve
    top_n_docs=3      # Documents to filter to
):
    # Stage 1: Find top-N documents using document embeddings
    top_documents = self.resource_repository.vector_search_documents(
        resource_ids=resource_ids,
        query_embedding=query_embedding,
        top_k=top_n_docs  # e.g., top 3 documents
    )

    # Stage 2: Search chunks only in those documents
    filtered_resource_ids = [doc["resource_id"] for doc in top_documents]
    hits = self.chunk_service.vector_search(
        resource_ids=filtered_resource_ids,
        query_embedding=query_embedding,
        top_k=top_k  # e.g., top 8 chunks
    )

    # Generate response using retrieved chunks
    ...
```

## API Usage

### Upload and Process Resource

```python
# 1. Upload file
POST /resources/upload
Content-Type: multipart/form-data
file: document.pdf

Response:
{
  "resource_id": "uuid-here",
  "filename": "document.pdf",
  ...
}

# 2. Process (generates both embeddings)
POST /resources/{resource_id}/process
{
  "doc_type": "teacher_guide"  # optional
}

Response:
{
  "resource_id": "uuid-here",
  "status": "completed",
  "chunks_created": 42,
  "message": "Resource processed successfully"
}
```

### Search Documents (Manual)

```python
from app.services.resource_service import ResourceService

# Get embedding for query
query = "What is photosynthesis?"
query_embedding = generate_embedding(query)

# Search documents
service = ResourceService(db)
top_docs = service.search_documents(
    resource_ids=[uuid1, uuid2, uuid3],
    query_embedding=query_embedding,
    top_k=3
)

# Result:
[
  {
    "resource_id": "uuid1",
    "original_filename": "biology.pdf",
    "similarity_score": 0.92
  },
  {
    "resource_id": "uuid3",
    "original_filename": "science.pdf",
    "similarity_score": 0.85
  },
  ...
]
```

### Full RAG Query (Uses Two-Stage Automatically)

```python
from app.services.rag_service import RAGService
from app.shared.ai.embeddings import generate_embedding

rag = RAGService(db)

# Generate embedding for query
query = "Explain the process of photosynthesis"
query_embedding = generate_embedding(query)

# Two-stage retrieval happens automatically
response = rag.generate_response(
    session_id=session_uuid,
    user_message_id=message_uuid,
    user_query=query,
    resource_ids=[doc1, doc2, doc3, doc4, doc5],
    query_embedding=query_embedding,
    top_k=8,         # Retrieve 8 chunks
    top_n_docs=3     # From top 3 documents only
)

# Response includes:
{
  "assistant_message_id": "uuid",
  "content": "Photosynthesis is...",
  "sources": [
    {"id": "chunk_uuid", "resource_id": "doc_uuid", "content": "...", ...},
    ...
  ]
}
```

## Performance Benefits

### Before (Single-Stage):

- Search space: ALL chunks in ALL documents
- If 10 documents × 50 chunks each = search 500 chunks
- Slower, less focused results

### After (Two-Stage):

- Stage 1: Search 10 document embeddings → find top 3 docs
- Stage 2: Search ~150 chunks (3 docs × 50 chunks)
- **70% reduction in search space**
- Faster + more relevant results

## Configuration

### Adjust Parameters:

```python
# In chat endpoint or RAG service call
response = rag.generate_response(
    ...,
    top_k=8,        # Number of chunks to retrieve (default: 8)
    top_n_docs=3    # Number of documents to filter to (default: 3)
)
```

### Recommendations:

- **top_n_docs**: 2-5 documents (balance speed vs coverage)
- **top_k**: 5-15 chunks (depends on context window)
- For large document sets (>10 docs): Increase `top_n_docs`
- For specific queries: Decrease `top_n_docs` to 2

## Database Indexing

The migration creates an IVFFlat index for fast document vector search:

```sql
CREATE INDEX idx_resource_files_doc_embedding
ON resource_files USING ivfflat (document_embedding vector_cosine_ops)
WITH (lists = 100);
```

Adjust `lists` parameter based on your data:

- Small dataset (<1K docs): 50-100 lists
- Medium dataset (1K-10K docs): 100-500 lists
- Large dataset (>10K docs): 500-1000 lists

## Monitoring

Track retrieval quality:

```python
# Log document filtering results
logger.info(f"Filtered from {len(resource_ids)} to {len(top_documents)} documents")
logger.info(f"Top doc similarities: {[d['similarity_score'] for d in top_documents]}")

# Log chunk retrieval from filtered docs
logger.info(f"Retrieved {len(hits)} chunks from {len(filtered_resource_ids)} documents")
```

## Fallbacks

The system gracefully handles missing embeddings:

1. If no document embeddings exist → searches all chunks directly
2. If query embedding not provided → returns first N chunks
3. If top_n_docs yields no results → falls back to all resources

## Example Query Flow

```
User Query: "How to solve quadratic equations?"
↓
1. Generate query embedding: [0.12, -0.43, 0.88, ...]
↓
2. Document Search (Stage 1):
   - Search 5 resources with document embeddings
   - Results:
     * algebra_guide.pdf (similarity: 0.94) ✓
     * math_exercises.pdf (similarity: 0.87) ✓
     * geometry_notes.pdf (similarity: 0.45) ✗
     * physics_basics.pdf (similarity: 0.32) ✗
     * chemistry_lab.pdf (similarity: 0.28) ✗
   - Selected: Top 2 documents (algebra, exercises)
↓
3. Chunk Search (Stage 2):
   - Search only chunks in algebra_guide.pdf & math_exercises.pdf
   - Total chunks: ~80 (instead of 200+ from all docs)
   - Retrieved top 8 most relevant chunks
↓
4. Generate Response:
   - Context: 8 focused chunks about quadratic equations
   - LLM generates answer using this context
```

## Testing

```bash
# 1. Apply migration
psql -U user -d sinhala_learn -f migrations/add_document_embeddings.sql

# 2. Process a resource (generates embeddings)
curl -X POST http://localhost:8000/resources/{id}/process

# 3. Test retrieval
# Use chat endpoint with multiple resources
# Check that only top-N documents are used for chunk retrieval
```

## Troubleshooting

### Document embeddings not generated?

- Check that `embed_document_text()` is called in resource processing
- Verify Gemini API key is configured
- Check logs for embedding errors

### Slow document search?

- Ensure IVFFlat index is created
- Run: `REINDEX INDEX idx_resource_files_doc_embedding;`
- Adjust `lists` parameter for your dataset size

### Empty results?

- Check if documents have embeddings:
  ```sql
  SELECT id, original_filename,
         document_embedding IS NOT NULL as has_embedding
  FROM resource_files;
  ```
- Reprocess resources if embeddings are missing

## Benefits Summary

✅ **Faster**: Reduce search space by 60-80%  
✅ **More Accurate**: Focus on relevant documents first  
✅ **Scalable**: Efficient for large document collections  
✅ **Flexible**: Configurable filtering parameters  
✅ **Robust**: Automatic fallbacks for edge cases
