"""Tests for the HTML pages of the shop."""
from datetime import UTC, datetime


def test_home_page_lists_products(client, latte):
    """The shop front page shows active products."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Latte" in response.text


def test_home_page_search_with_no_match(client, latte):
    """Searching for something that doesn't exist shows a friendly message."""
    response = client.get("/", params={"q": "pizza"})
    assert "No products match your search" in response.text


def test_empty_category_filter_does_not_error(client, latte):
    """'All categories' sends an empty value, which must not cause an error."""
    assert client.get("/", params={"category_id": ""}).status_code == 200


def test_product_page_shows_product_and_tracks_view(client, latte, mongo_db):
    """The product page renders and records a product_view event."""
    response = client.get(f"/products/{latte.id}")
    assert response.status_code == 200
    assert "£3.20" in response.text
    assert mongo_db.events.find_one({"type": "product_view"}) is not None


def test_unknown_product_page_returns_404(client):
    """A missing product shows the not-found page with a 404 status."""
    response = client.get("/products/999")
    assert response.status_code == 404
    assert "couldn't find that" in response.text


def test_review_comments_are_escaped(client, latte, mongo_db):
    """A malicious review comment is shown as text, not run as a script (XSS protection)."""
    mongo_db.reviews.insert_one(
        {
            "product_id": latte.id,
            "user_id": 1,
            "author_name": "Mallory",
            "rating": 1,
            "comment": "<script>alert('hacked')</script>",
            "helpful_votes": [],
            "created_at": datetime.now(UTC),
        }
    )
    html = client.get(f"/products/{latte.id}").text
    assert "<script>alert('hacked')</script>" not in html
    assert "&lt;script&gt;" in html


def test_nav_changes_when_logged_in(client, customer):
    """Logged-out visitors see Log in; logged-in customers see Log out."""
    assert "Log out" in customer.get("/").text
    customer.post("/api/v1/auth/logout")
    assert "Log in" in customer.get("/").text