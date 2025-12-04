from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router

app = FastAPI(
    title="Sinhala Educational Assistant API",
    version="1.0.0",
    description="Backend for Sinhala Document Processing, Q&A, Evaluation, and Voice features.",
)

# CORS (adjust origins for your frontend later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount versioned API
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "message": "Sinhala-Ed-Assistant API is running 🚀"}
