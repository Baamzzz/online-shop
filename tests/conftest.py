"""Shared pytest fixtures."""
from decimal import Decimal

import mongomock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.rate_limit import limiter
from app.db.mongo import get_mongo
from app.db.session import Base, get_db
from app.main import app
from app.models import Product, User
from tests.test_auth import login, register


@pytest.fixture
def db_session():
    """A fresh in-memory SQLite database for each test, so tests never touch Neon."""
    # StaticPool + check_same_thread=False let the test client share this one in-memory DB
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def mongo_db():
    """An in-memory fake MongoDB for each test, so tests never touch Atlas."""
    return mongomock.MongoClient()["test_shop"]


@pytest.fixture
def client(db_session, mongo_db):
    """A test client whose requests use the test databases instead of Neon and Atlas."""
    limiter.reset()  # Start every test with a clean rate-limit count
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_mongo] = lambda: mongo_db
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


@pytest.fixture
def customer(client):
    """A test client logged in as a customer."""
    register(client)
    login(client)
    return client


@pytest.fixture
def latte(db_session):
    """A product with 5 in stock."""
    product = Product(name="Latte", price=Decimal("3.20"), stock=5)
    db_session.add(product)
    db_session.commit()
    return product