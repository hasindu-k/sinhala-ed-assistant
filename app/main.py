# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.database import Base, engine
from components.evaluation.routers.evaluation_router import router as EvaluationRouter


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
app.include_router(EvaluationRouter)


# ------------------------------------------------------------
# Health Check Endpoint
# ------------------------------------------------------------
@app.get("/")
def root():
    return {"status": "OK", "message": "SinhalaLearn Backend Running"}
