"""Tests for registration, login, logout and password security."""
from sqlalchemy import select

from app.core.security import hash_password, verify_password
from app.models import User

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
EMAIL = "alice@example.com"
PASSWORD = "CorrectHorse1"


def register(client, email=EMAIL, password=PASSWORD):
    """Helper: register a user through the API."""
    return client.post(
        REGISTER_URL, json={"email": email, "full_name": "Alice", "password": password}
    )


def login(client, password=PASSWORD):
    """Helper: log in through the API."""
    return client.post(LOGIN_URL, json={"email": EMAIL, "password": password})


def test_hash_and_verify_password():
    """A hash should verify with the right password and fail with the wrong one."""
    hashed = hash_password(PASSWORD)
    assert verify_password(PASSWORD, hashed)
    assert not verify_password("WrongPassword1", hashed)


def test_register_returns_user_without_password(client):
    """Registering returns 201 and never exposes the password or hash."""
    response = register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == EMAIL
    assert "password" not in body
    assert "password_hash" not in body

def test_password_is_stored_as_argon2_hash(client, db_session):
    """The database must hold an Argon2id hash, not the plain password."""
    register(client)
    user = db_session.scalar(select(User))
    assert user.password_hash != PASSWORD
    assert user.password_hash.startswith("$argon2id$")


def test_short_password_is_rejected(client):
    """Validation should reject passwords under 8 characters."""
    assert register(client, password="short").status_code == 422


def test_duplicate_email_returns_409(client):
    """The same email can't register twice."""
    register(client)
    assert register(client).status_code == 409


def test_login_sets_httponly_cookie_and_unlocks_me(client):
    """A successful login sets an HttpOnly Cookie that grants acces to /me"""
    register(client)
    response = login(client)
    assert response.status_code == 200
    assert "httponly" in response.headers["set-cookie"].lower()
    assert client.get("/api/v1/auth/me").json()["email"] == EMAIL


def test_wrong_password_returns_401(client):
    """A wrong passworod is rejected."""
    register(client)
    assert login(client, password="WrongPassword1").status_code == 401


def test_me_requires_login(client):
    """Protected routes return 401 without a valid cookie."""
    assert client.get("/api/v1/auth/me").status_code == 401


def test_logged_out_token_cannot_be_reused(client):
    """After logout, even a stolen copy of the token must stop working."""
    register(client)
    login(client)
    stolen_token = client.cookies.get("access_token")
    client.post("/api/v1/auth/logout")

    client.cookies.set("access_token", stolen_token)
    assert client.get("/api/v1/auth/me").status_code == 401
