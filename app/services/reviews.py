"""Product review logic. Reviews live in MongoDB; purchase checks use Postgres."""
from datetime import UTC, datetime

from bson import ObjectId
from pymongo.database import Database
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Order, OrderItem, User
from app.schemas.review import ReviewIn, ReviewOut, ReviewSummary


class ReviewError(Exception):
    """A review rule was broken. Carries the HTTP status code the route should return."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


def _public_name(full_name: str) -> str:
    """Show 'Diogo D.' rather than a full name, to protect reviewers' privacy."""
    parts = full_name.split()
    return f"{parts[0]} {parts[-1][0]}." if len(parts) > 1 else parts[0]


def _to_out(doc: dict) -> ReviewOut:
    """Convert a MongoDB document into the API's response shape."""
    return ReviewOut(
        id=str(doc["_id"]),
        product_id=doc["product_id"],
        author_name=doc["author_name"],
        rating=doc["rating"],
        comment=doc.get("comment"),  # .get becuase the field only exists if written
        helpful_votes=len(doc.get("helpful_votes", [])),
        created_at=doc["created_at"],
    )


def has_bought(db: Session, user_id: int, product_id: int) -> bool:
    """True if the user has ever ordered this product (a Postgres query)."""
    query = (
        select(OrderItem.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.user_id == user_id, OrderItem.product_id == product_id)
        .limit(1)
    )
    return db.scalar(query) is not None


def add_review(db: Session, mongo: Database, user: User, product_id: int, data: ReviewIn) -> ReviewOut:
    """Save a review from a verified buyer. One review per customer per product."""
    if not has_bought(db, user.id, product_id):
        raise ReviewError(403, "Only customers who bought this product can review it")
    if mongo.reviews.find_one({"product_id": product_id, "user_id": user.id}):
        raise ReviewError(409, "You have already reviewed this product")

    doc = {
        "product_id": product_id,
        "user_id": user.id,
        "author_name": _public_name(user.full_name),
        "rating": data.rating,
        "helpful_votes": [],
        "created_at": datetime.now(UTC),
    }
    if data.comment and data.comment.strip():
        doc["comment"] = data.comment.strip() # Only stored when there is one


    doc["_id"] = mongo.reviews.insert_one(doc).inserted_id
    return _to_out(doc)

def product_reviews(mongo: Database, product_id: int, limit: int = 20) -> ReviewSummary:
    """Average rating and count (via an aggregation pipeline) plus the newest reviews."""
    stats = list(
        mongo.reviews.aggregate(
            [
                {"$match": {"product_id": product_id}},
                {"$group": {"_id": None, "average": {"$avg": "$rating"}, "count": {"$sum": 1}}},
            ]
        )
    )
    docs = mongo.reviews.find({"product_id": product_id}).sort("created_at", -1).limit(limit)

    # Only use the stats if at least one review matched (mongomock, and some MongoDB
    # versions, return a group with a None average when nothing matched)
    summary = stats[0] if stats and stats[0]["count"] else None
    return ReviewSummary(
        average_rating=round(summary["average"], 1) if summary else None,
        review_count=summary["count"] if summary else 0,
        reviews=[_to_out(doc) for doc in docs],
    )

def mark_helpful(mongo: Database, review_id: str, user_id: int) -> None:
    """Record a 'helpful' vote. $addToSet means each user's vote counts only once."""
    if not ObjectId.is_valid(review_id):
        raise ReviewError(404, "Review not found")
    doc = mongo.reviews.find_one({"_id": ObjectId(review_id)})
    if doc is None:
        raise ReviewError(404, "Review not found")
    if doc["user_id"] == user_id:
        raise ReviewError(400, "You can't vote on your own review")
    mongo.reviews.update_one({"_id": doc["_id"]}, {"$addToSet": {"helpful_votes": user_id}})