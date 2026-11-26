"""Entry point for the FastAPI application"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1 import admin, auth, cart, orders, products, reviews
from app.core.config import settings
from app.core.rate_limit import limiter
from app.web import pages

app = FastAPI(title=settings.app_name, version="0.1.0")

# Signed session cookie, used only to hold the OAuth state during Google sign-in
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key,
    https_only=settings.cookie_secure,
    same_site="lax",
)

# Rate limiting: returns 429 Too Many Requests when a limit is exceeded
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")
app.include_router(cart.router, prefix="/api/v1")
app.include_router(reviews.router, prefix="/api/v1")
# Front end: static files (CSS/JS) and the HTML pages
app.mount("/static", StaticFiles(directory=Path(__file__).resolve().parent / "static"), name="static")
app.include_router(pages.router)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """liveness check, used by tests and later by Cloud Run."""
    return{"status": "ok"}