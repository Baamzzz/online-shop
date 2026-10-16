"""Command-line admin tools. Usage python -m app.cli make-admin someone@example.com"""
import sys

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import User


def make_admin(email: str) -> None:
    """Give an existing user the admin role."""
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email.lower()))
        if user is None:
            sys.exit(f"No user found with email {email}")
        user.role = "admin"
        db.commit()
        print(f"{email} is now an admin")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "make-admin":
        sys.exit("Usage: python -m app.cli make-admin <email>")
    make_admin(sys.argv[2])