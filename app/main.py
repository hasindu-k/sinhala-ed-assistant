from fastapi import FastAPI
from dotenv import load_dotenv
from app.api.v1.router import api_router
from typing import Optional

load_dotenv()  # Load environment variables

# Create FastAPI application
app = FastAPI(
    title="Sinhala Educational Assistant Backend",
    version="1.0.0",
    description="ASR + RAG + OCR + Evaluation System"
)

# Include API routes
app.include_router(api_router)


# Health check endpoint
@app.get("/")
def read_root():
    return {"status": "running"}


# Example route (fixed for Python 3.9)
@app.get("/items/{item_id}")
def read_item(item_id: int, q: Optional[str] = None):
    return {"item_id": item_id, "query": q}
