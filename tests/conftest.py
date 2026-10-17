"""Shared pytest fixtures."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models
from app.core.rate_limit import limiter
from app.db.session import Base, get_db
from app.main import app
from app.models import User


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
    limiter.reset() # Start every test with a clean rate-limit count
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_client(client, db_session):
    """A test client already logged in as an admin."""
    credentials = {"email": "admin@example.com", "password": "AdminPass123"}
    client.post("/api/v1/auth/register", json={**credentials, "full_name": "Admin"})
    admin = db_session.scalar(select(User).where(User.email == "admin@example.com"))
    admin.role = "admin"
    db_session.commit()
    client.post("/api/v1/auth/login", json=credentials)
    return client
