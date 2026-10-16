"""Admin-only routes. Every route in this router requires the admin role."""
from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.core.deps import DbSession, require_admin
from app.models import User
from app.schemas.user import UserOut

# Applying require_admin at router level makes every route here admin-only by default,
# so a new admin route can't accidentally be left unprotected
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/users", response_model=list[UserOut])
def list_users(db: DbSession) -> list[User]:
    """List all user accounts."""
    return list(db.scalars(select(User).order_by(User.id)))