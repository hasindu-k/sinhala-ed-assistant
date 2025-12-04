# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine
from app.core.config import settings
from app.components.evaluation.routers.evaluation_router import router as evaluation_router


# ------------------------------------------------------------
# Create all DB tables at startup
# ------------------------------------------------------------
Base.metadata.create_all(bind=engine)



# ------------------------------------------------------------
# CORS (Allow web + mobile frontend)
# ------------------------------------------------------------
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


# ------------------------------------------------------------
# Include Routers
# ------------------------------------------------------------
app.include_router(evaluation_router)


# ------------------------------------------------------------
# Health Check Endpoint
# ------------------------------------------------------------
@app.get("/")
def root():
    return {"status": "OK", "message": "SinhalaLearn Backend Running"}
