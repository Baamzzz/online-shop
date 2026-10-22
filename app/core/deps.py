"""Reusable FastAPI dependencies for database access and authentication."""
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from pymongo.database import Database
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.mongo import get_mongo
from app.db.session import get_db
from app.models import RevokedToken, User

COOKIE_NAME = "access_token"

DbSession = Annotated[Session, Depends(get_db)]

_unauthorised = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
)



def get_current_user(request: Request, db: DbSession) -> User:
    """Return the logged-in user from the auth cookie, or raise 401."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise _unauthorised
    try:
        payload = decode_access_token(token)
    except jwt.InvalidTokenError:
        raise _unauthorised from None
    # Reject tokens that were logged out before they expire
    if db.get(RevokedToken, payload["jti"]):
        raise _unauthorised
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise _unauthorised
    return user

CurrentUser = Annotated[User, Depends(get_current_user)]

def require_admin(user: CurrentUser) -> User:
    """Allow only admins through. Logged-in customers get 403 Forbidden."""
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin Access required")
    return user


AdminUser = Annotated[User, Depends(require_admin)]

MongoDB = Annotated[Database, Depends(get_mongo)]