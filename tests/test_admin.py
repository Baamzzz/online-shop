"""Tests for admin-only access control."""
from sqlalchemy import select

from app.models import User
from tests.test_auth import login, register

USERS_URL = "/api/v1/admin/users"


def test_admin_route_requires_login(client):
    """Anonymous users get 401."""
    assert client.get(USERS_URL).status_code == 401


def test_admin_route_rejects_customers(client):
    """Logged-in customers get 403."""
    register(client)
    login(client)
    assert client.get(USERS_URL).status_code == 403


def test_admin_can_list_users(client, db_session):
    """A user promoted to admin can access admin routes."""
    register(client)
    user = db_session.scalar(select(User))
    user.role = "admin"
    db_session.commit()

    login(client)
    response = client.get(USERS_URL)
    assert response.status_code == 200
    assert len(response.json()) == 1