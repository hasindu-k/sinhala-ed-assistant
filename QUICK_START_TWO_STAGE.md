# Quick Start: Two-Stage Retrieval

## Setup (One-Time)

### 1. Run Database Migration

```bash
psql -U your_user -d sinhala_learn -f migrations/add_document_embeddings.sql
```

This adds:

- `document_embedding` column to `resource_files` table
- `embedding_model` column
- Vector index for fast document search

### 2. Reprocess Existing Resources (Optional)

If you have existing resources without document embeddings:

```python
from app.services.resource_service import ResourceService
from sqlalchemy.orm import Session

# For each resource
service = ResourceService(db)
service.process_resource(
    resource_id=your_resource_id,
    user_id=owner_id
)
```

Or via API:

```bash
POST /resources/{resource_id}/process
```

## Usage

### Automatic (RAG Service)

The two-stage retrieval is **already integrated** into the RAG service. Just use it normally:

```python
from app.services.rag_service import RAGService
from app.shared.ai.embeddings import generate_embedding

# Initialize service
rag = RAGService(db)

# Generate query embedding
query = "Your question here"
query_embedding = generate_embedding(query)

# Call RAG service (two-stage happens automatically)
response = rag.generate_response(
    session_id=session_id,
    user_message_id=message_id,
    user_query=query,
    resource_ids=[doc1, doc2, doc3, doc4, doc5],  # 5 documents
    query_embedding=query_embedding,
    top_k=8,         # Get 8 chunks
    top_n_docs=3     # From top 3 documents (auto-filtered)
)
```

**What happens:**

1. System searches 5 documents → finds top 3 most relevant
2. Searches chunks only in those 3 documents
3. Returns top 8 chunks from filtered documents
4. Generates response

### Manual Document Search

To see which documents are most relevant:

```python
from app.services.resource_service import ResourceService

service = ResourceService(db)
top_docs = service.search_documents(
    resource_ids=[doc1, doc2, doc3],
    query_embedding=query_embedding,
    top_k=3
)

# Results:
# [
#   {"resource_id": "...", "original_filename": "math.pdf", "similarity_score": 0.92},
#   {"resource_id": "...", "original_filename": "algebra.pdf", "similarity_score": 0.85},
#   ...
# ]
```

## Configuration

### Tune Parameters for Your Use Case:

```python
# More focused (fewer documents, precise results)
response = rag.generate_response(
    ...,
    top_k=5,
    top_n_docs=2  # Very focused on top 2 docs
)

# Broader coverage (more documents, diverse results)
response = rag.generate_response(
    ...,
    top_k=15,
    top_n_docs=5  # Search more documents
)
```

### Recommendations:

| Scenario                   | top_n_docs | top_k | Reasoning      |
| -------------------------- | ---------- | ----- | -------------- |
| Small doc set (2-5 docs)   | 2-3        | 8-10  | High precision |
| Medium doc set (5-20 docs) | 3-5        | 8-15  | Balanced       |
| Large doc set (20+ docs)   | 5-8        | 10-20 | Broad coverage |
| Specific queries           | 2-3        | 5-8   | Very focused   |
| General queries            | 4-6        | 10-15 | More diverse   |

## Verify It's Working

### Check Document Embeddings:

```sql
SELECT
    id,
    original_filename,
    document_embedding IS NOT NULL as has_doc_embedding,
    embedding_model
FROM resource_files
ORDER BY created_at DESC
LIMIT 10;
```

### Monitor Retrieval:

```python
# Enable debug logging
import logging
logging.getLogger('app.services.rag_service').setLevel(logging.DEBUG)

# Check logs for:
# - "Filtered from X to Y documents"
# - Document similarity scores
# - Number of chunks searched
```

## Common Issues

### ❌ No results returned

**Cause:** Documents don't have embeddings  
**Fix:** Reprocess resources with `POST /resources/{id}/process`

### ❌ Slow performance

**Cause:** Index not created or needs rebuilding  
**Fix:**

```sql
REINDEX INDEX idx_resource_files_doc_embedding;
```

### ❌ Low quality results

**Cause:** `top_n_docs` too low  
**Fix:** Increase to 4-5 documents

## That's It!

The two-stage retrieval is now active. Every RAG query automatically:

1. ✅ Filters documents by relevance (fast)
2. ✅ Searches chunks in top documents (focused)
3. ✅ Returns better, faster results

No code changes needed in your endpoints - it just works! 🎉
