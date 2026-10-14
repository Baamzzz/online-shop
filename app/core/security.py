"""Password hashing (Argon2id) and JWT access token helpers."""
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import settings

# Argon2id with the library's recommended defaults (salted automatically)
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Return a salted Argon2id hash. The plain password is never stored."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Check a password against a stored hash, returning False instead of raising."""
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(user_id: int, role: str) -> str:
    """Create a signed, short-lived JWT. 'jti' is a unique ID so it can be revoked on logout."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)



def decode_access_token(token: str) -> dict:
    """Verify the signature and expiry. Raises jwt.InvalidTokenError if either fails."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])