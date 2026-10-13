"""Shared pytest fixtures."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers all models)
from app.db.session import Base


@pytest.fixture
def db_session():
    """A fresh in-memory SQLite database for each test, so tests never touch Neon."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()