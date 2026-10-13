"""Database engine and session setup for the SQL (Neon Postgres) database."""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# pool_pre_ping tests each connection before use, since Neon closes idle connections
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class that every SQLAlchemy model inherits from."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: provides a database session and always closes it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()