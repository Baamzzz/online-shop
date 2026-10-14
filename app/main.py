"""Entry point for the FastAPI application"""
from fastapi import FastAPI

from app.api.v1 import auth
from app.core.config import settings

app = FastAPI(title=settings.app_name, version="0.1.0")
app.include_router(auth.router, prefix="/api/v1")

@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """liveness check, used by tests and later by Cloud Run."""
    return{"status": "ok"}