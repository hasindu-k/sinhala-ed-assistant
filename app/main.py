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
# FastAPI App
# ------------------------------------------------------------
app = FastAPI(
    title="SinhalaLearn Backend",
    description="AI-Powered Sinhala Education Assistant API",
    version="1.0.0"
)


# ------------------------------------------------------------
# CORS (Allow web + mobile frontend)
# ------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # change later to your domains
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
