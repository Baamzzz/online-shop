"""MongoDB Atlas connection, used for flexible, fast-chargin data (carts, reviews, events)."""
from functools import lru_cache

from pymongo import MongoClient
from pymongo.database import Database

from app.core.config import settings


@lru_cache
def get_client() -> MongoClient:
    """One client for the whole app. It manages its own pool of connections."""
    return MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=5000)


def get_mongo() -> Database:
    """FastAPI dependency: the app's MongoDB database."""
    return get_client()[settings.mongo_db_name]