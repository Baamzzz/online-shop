"""Entry point for the FastAPI application"""
from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(title=settings.app_name, version="0.1.0")


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """liveness check, used by tests and later by Cloud Run."""
    return{"status": "ok"}