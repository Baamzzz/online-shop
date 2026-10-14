"""Revoked token model: a denylist so logged-out token can't be reused."""
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class RevokedToken(Base):
    """A token ID (jti) that was logged out before it it expired."""

    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    # Stored so expired entries can be cleaned up later (a cloud function job)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))