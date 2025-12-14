# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router  
from app.core.database import Base, engine

# # Import models to register them with Base
# from app.shared.models.user_chat import UserChat
# from app.shared.models.resource_data import ResourceData
# from app.shared.models.chat_messages import ChatMessage

# Create tables (only needed once, will skip if already exist)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sinhala Educational Assistant API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"status": "OK"}
