"""Authentication business login, kept separate from routes so it can be unit tested."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


def get_or_create_google_user(db: Session, info: dict) -> User:
    """Find the user for a verified Google identify, linking or creating an account."""
    google_id = info["sub"] # Google's permanent, unique ID for this person
    email= info["email"].lower()

    user = db.scalar(select(User).where(User.google_id == google_id))
    if user is None:
        user = db.scalar(select(User).where(User.email == email))
        if user is not None:
            # Existing password account with the same verified email: link it to Google
            user.google_id = google_id
        else:
            # New customer: Google accounts have no password in our database
            user = User(email=email, full_name=info.get("name") or email, google_id=google_id)
            db.add(user)
        db.commit()
        db.refresh(user)
    return user