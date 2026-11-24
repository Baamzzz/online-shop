"""Event tracking: records what shoppers do, for analytics and recommendations.

Each event type has its own shape, which suits MongoDB'S flexible documents:
    {"type": "product_view", "user_id": 7,    "product_id": 3}
    {"type": "search",       "user_id": None, "query": "latte"}
    {"type": "add_to_cart",  "user_id": 7,    "product_id": 3, "quantity": 2}
    {"type": "checkout",     "user_id": 7,    "order_id": 12, "total": "6.40"}
Every event also gets a created_at time.
"""

import logging
from datetime import UTC, datetime, timedelta

from pymongo.database import Database
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Current UTC time without timezone info, matching how PyMongo returns stored dates."""
    return datetime.now(UTC).replace(tzinfo=None)


def track(mongo: Database, event_type: str, user_id: int | None, **details) -> None:
    """Record an event. Tracking must never break the shop, so errors are logged, not raised."""
    try:
        mongo.events.insert_one(
            {"type": event_type, "user_id": user_id, **details, "created_at": _utc_now()}
        )
    except PyMongoError:
        logger.warning("Could not record %s event", event_type, exc_info=True)


def most_viewed(mongo: Database, days: int, limit: int = 5) -> list[dict]:
    """Aggregation pipeline: count product views in the last N days, most viewed first."""
    pipeline = [
        {"$match": {"type": "product_view", "created_at": {"$gte": _utc_now() - timedelta(days=days)}}},
        {"$group": {"_id": "$product_id", "views": {"$sum": 1}}},
        {"$sort": {"views": -1}},
        {"$limit": limit},    
    ]
    return list(mongo.events.aggregate(pipeline))

def top_searches(mongo: Database, days: int, limit: int = 5) -> list[dict]:
    """Aggregation pipeline: the most common search terms in the last N days."""
    pipeline = [
        {"$match": {"type": "search", "created_at": {"$gte": _utc_now() - timedelta(days=days)}}},
        {"$group": {"_id": "$query", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]
    return list(mongo.events.aggregate(pipeline))