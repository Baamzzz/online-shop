"""Authentication route: register, login, logout and current user."""
from datetime import UTC, datetime

import jwt
from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import COOKIE_NAME, CurrentUser, DbSession
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models import RevokedToken, User
from app.schemas.user import UserCreate, UserLogin, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: DbSession) -> User:
    """Create a customer account with a hashed password."""
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    user = User(email=email, full_name=data.full_name, password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=UserOut)
@limiter.limit("5/minute")
def login(request: Request, data: UserLogin, response: Response, db: DbSession) -> User:
    """Check credentials and set the JWT in an HttpOnly cookie."""
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    # One generic error for unknown email AND wrong password,
    # so attackers can't use login to discore which emails have accounts
    if (
        user is None
        or user.password_hash is None
        or not verify_password(data.password, user.password_hash)
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    token = create_access_token(user.id, user.role)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True, # JavaScript can't read it, protecting against XSS token theft
        secure=settings.cookie_secure, #HTTPS only in production
        samesite="lax", # not sent on cross-site POSTs, helping against CSRF
        max_age=settings.access_token_expire_minutes * 60,
    )
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: DbSession) -> None:
    """Revoke the current token and clear the cookie"""
    token = request.cookies.get(COOKIE_NAME)
    if token:
        try:
            payload = decode_access_token(token)
            db.merge(
                RevokedToken(
                    jti=payload["jti"],
                    expires_at=datetime.fromtimestamp(payload["exp"], UTC),
                )
            )
            db.commit()
        except jwt.InvalidTokenError:
            pass # Token already invalid or expired, so there's nothing to revoke
        response.delete_cookie(COOKIE_NAME)


@router.get("/me", response_model=UserOut)
def read_me(user: CurrentUser) -> User:
    """Return the logged-in user. A simpled protected route."""
    return user