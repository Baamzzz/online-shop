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


def test_cart_page_requires_login(client):
    """Visitors who aren't loggen in are sent to the login page."""
    response = client.get("/cart", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_cart_page_shows_items_and_subtotal(customer, latte):
    """The cart page lists items with live prices and a subtotal."""
    customer.put("/api/v1/cart/items", json={"product_id": latte.id, "quantity": 2})
    html = customer.get("/cart").text
    assert "Latte" in html
    assert "£6.40" in html


def test_empty_cart_page(customer):
    """An empty cart shows a friendly message instead of a table."""
    assert "Your cart is empty" in customer.get("/cart").text


def test_orders_page_shows_order_history(customer, latte):
    """Placed orders appear on the My orders page with their total."""
    customer.post("/api/v1/orders", json={"items": [{"product_id": latte.id, "quantity": 1}]})
    html = customer.get("/orders").text
    assert "1 × Latte" in html
    assert "Total £3.20" in html


def test_admin_page_is_hidden_from_customers(customer):
    """Customers get the not-found page, not the dashboard."""
    response = customer.get("/admin")
    assert response.status_code == 404
    assert "Admin dashboard" not in response.text


def test_admin_page_shows_low_stock(admin_client, latte):
    """Admins see the dashboard, icluding products running low (Latte has 5)."""
    html = admin_client.get("/admin").text
    assert "Admin dashboard" in html
    assert "Latte (5 left)" in html