"""Shared pytest fixtures."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers all models)
from app.db.session import Base, get_db
from app.main import app


@pytest.fixture
def db_session():
    """A fresh in-memory SQLite database for each test, so tests never touch Neon."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass= StaticPool
        )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def client(db_session):
    """A test client whose requests use the test database instead of Neon."""
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()