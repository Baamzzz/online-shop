"""Authentication route: register, login, logout and current user."""
from datetime import UTC, datetime

import jwt
from authlib.integrations.starlette_client import OAuthError
from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import COOKIE_NAME, CurrentUser, DbSession
from app.core.oauth import oauth
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models import RevokedToken, User
from app.schemas.user import UserCreate, UserLogin, UserOut
from app.services.auth import get_or_create_google_user


def _set_auth_cookie(response: Response, user: User) -> None:
    """Issue a JWT for the user and store it in a secure HttpOnly cookie"""
    response.set_cookie(
        key=COOKIE_NAME,
        value=create_access_token(user.id, user.role),
        httponly=True, # Javascript can't read it, protecting against XSS token theft
        secure=settings.cookie_secure, # HTTPS only in production
        samesite="lax", # not sent on cross-site POSTs, helping against CSRF
        max_age=settings.access_token_expire_minutes * 60,
    )

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

    _set_auth_cookie(response, user)
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

@router.get("/google/login")
async def google_login(request: Request):
    """Send the user to Google's sign-in page."""
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/google/callback", name="google_callback")
async def google_callback(request: Request, db: DbSession) -> RedirectResponse:
    """Google sends the user back here. Verify them, then log them in."""
    try:
        # Authlib checks the state value (CSRF protection) and the ID token's signature
        token = await oauth.google.authorize_access_token(request)
    except OAuthError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Google sign-in failed") from None

    info = token.get("userinfo")
    if not info or not info.get("email_verified"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Google email is not verified")

    user = get_or_create_google_user(db, info)
    # Redirect to the docs for now; this becomes the shop home page in the front-end stage
    response = RedirectResponse(url="/docs", status_code=status.HTTP_303_SEE_OTHER)
    _set_auth_cookie(response, user)
    return response