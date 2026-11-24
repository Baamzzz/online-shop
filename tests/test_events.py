"""Tests for event tracking and admin analytics."""
from pymongo.errors import PyMongoError

from app.services.events import track


def test_viewing_a_product_records_an_event(client, latte, mongo_db):
    """Anonymous product views are recorded without a user."""
    client.get(f"/api/v1/products/{latte.id}")
    event = mongo_db.events.find_one({"type": "product_view"})
    assert event["product_id"] == latte.id
    assert event["user_id"] is None


def test_logged_in_views_record_the_user(customer, latte, mongo_db):
    """When a customer is logged in, their user ID is recorded."""
    customer.get(f"/api/v1/products/{latte.id}")
    assert mongo_db.events.find_one({"type": "product_view"})["user_id"] is not None


def test_search_terms_are_normalised(client, latte, mongo_db):
    """Searches are stored trimmed and lowercased so they group together."""
    client.get("/api/v1/products", params={"q": "  LATTE "})
    assert mongo_db.events.find_one({"type": "search"})["query"] == "latte"


def test_add_to_cart_and_checkout_are_tracked(customer, latte, mongo_db):
    """Cart and checkout actions each create their own type of event."""
    customer.put("/api/v1/cart/items", json={"product_id": latte.id, "quantity": 2})
    customer.post("/api/v1/cart/checkout", json={})
    types = {event["type"] for event in mongo_db.events.find()}
    assert {"add_to_cart", "checkout"} <= types


def test_admin_analytics_shows_views_and_searches(admin_client, latte):
    """The aggregation pipelines count views and searches correctly."""
    for _ in range(3):
        admin_client.get(f"/api/v1/products/{latte.id}")
    admin_client.get("/api/v1/products", params={"q": "latte"})

    data = admin_client.get("/api/v1/admin/analytics").json()
    assert data["most_viewed"][0] == {"product_id": latte.id, "name": "Latte", "views": 3}
    assert data["top_searches"][0] == {"query": "latte", "count": 1}


def test_customers_cannot_see_analytics(customer):
    """Analytics are admin-only."""
    assert customer.get("/api/v1/admin/analytics").status_code == 403


def test_tracking_failure_does_not_raise():
    """If MongoDB is down, tracking logs a warning instead of crashing the request."""

    class BrokenMongo:
        @property
        def events(self):
            raise PyMongoError("Atlas is unreachable")

    track(BrokenMongo(), "product_view", None, product_id=1)  # Must not raise