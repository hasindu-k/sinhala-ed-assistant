# app/main.py

from app.logging_config import setup_logging

setup_logging()

import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.api.v1.router import api_router
from app.core.database import Base, engine

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sinhala Educational Assistant API",
    version="1.0.0",
    swagger_ui_parameters={"persistAuthorization": True},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    logger.info("Starting Sinhala Educational Assistant API...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified successfully")
    except Exception as e:
        logger.warning(
            "Could not connect to database during startup: %s. "
            "The application will start but database operations may fail. "
            "Ensure PostgreSQL is running on the configured host and port.",
            str(e)
        )


def custom_openapi():
    """Add Bearer auth security scheme to OpenAPI and apply to protected endpoints."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Replace any auto-generated schemes with a single BearerAuth scheme
    openapi_schema.setdefault("components", {})["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }

    # Public endpoints that don't require auth
    public_paths = {
        "/api/v1/auth/signup",
        "/api/v1/auth/signin",
        "/api/v1/auth/forgot-password",
        "/api/v1/auth/reset-password",
        "/api/v1/auth/refresh",
        "/",
    }

    # HTTP methods to check
    http_methods = {"get", "post", "put", "delete", "patch", "options", "head"}

    # Apply security only to protected endpoints
    for path, path_item in openapi_schema.get("paths", {}).items():
        for method in http_methods:
            if method in path_item and path not in public_paths:
                operation = path_item[method]
                if isinstance(operation, dict):
                    operation["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"status": "OK"}

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")