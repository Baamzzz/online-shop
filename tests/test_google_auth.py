"""Tests fir matching Google identities to user accounts."""
from sqlalchemy import func, select

from app.models import User
from app.services.auth import get_or_create_google_user

GOOGLE_INFO = {"sub": "google-123", "email": "Bob@Gmail.com", "name": "Bob"}


def test_new_google_user_is_created_without_password(db_session):
    """A first-time Google user gets an account with no password hash."""
    user = get_or_create_google_user(db_session, GOOGLE_INFO)
    assert user.email == "bob@gmail.com"
    assert user.google_id == "google-123"
    assert user.password_hash is None


def test_existing_email_is_linked_not_duplicated(db_session):
    """A password account with the same email gets linked to Google."""
    db_session.add(User(email="bob@gmail.com", full_name="Bob", password_hash="hash"))
    db_session.commit()

    user = get_or_create_google_user(db_session, GOOGLE_INFO)
    assert user.google_id == "google-123"
    assert db_session.scalar(select(func.count()).select_from(User)) == 1


def test_returning_google_user_gets_same_account(db_session):
    """Signing in with Google twice returns the same user."""
    first = get_or_create_google_user(db_session, GOOGLE_INFO)
    second = get_or_create_google_user(db_session, GOOGLE_INFO)
    assert first.id == second.id


def test_google_only_account_cannot_use_password_login(client, db_session):
    """Accounts created via Google have no password, so password login must fail."""
    get_or_create_google_user(db_session, GOOGLE_INFO)
    response = client.post(
        "/api/v1/auth/login", json={"email": "bob@gmail.com", "password": "anything123"}
    )
    assert response.status_code == 401