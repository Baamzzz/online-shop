"""Tests for product reviews: verified buyers, one review each, ratings and helpful votes."""
from tests.test_auth import LOGIN_URL, PASSWORD, register


def buy(client, product_id):
    """Helper: order one of a product so the user becomes a verified buyer."""
    client.post("/api/v1/orders", json={"items": [{"product_id": product_id, "quantity": 1}]})


def review(client, product_id, rating=5, comment="Lovely"):
    """Helper: post a review. Pass comment=None to leave it out."""
    payload = {"rating": rating}
    if comment is not None:
        payload["comment"] = comment
    return client.post(f"/api/v1/products/{product_id}/reviews", json=payload)


def switch_to_eve(client):
    """Helper: log out and log in as a second customer."""
    client.post("/api/v1/auth/logout")
    register(client, email="eve@example.com")
    client.post(LOGIN_URL, json={"email": "eve@example.com", "password": PASSWORD})


def test_verified_buyer_can_review(customer, latte):
    """A customer who bought the product can review it, and it shows up with a summary."""
    buy(customer, latte.id)
    assert review(customer, latte.id, rating=4).status_code == 201

    summary = customer.get(f"/api/v1/products/{latte.id}/reviews").json()
    assert summary["review_count"] == 1
    assert summary["average_rating"] == 4.0
    assert summary["reviews"][0]["author_name"] == "Alice"


def test_must_have_bought_to_review(customer, latte):
    """Customers who never ordered the product get 403."""
    assert review(customer, latte.id).status_code == 403


def test_only_one_review_per_product(customer, latte):
    """A second review of the same product is rejected."""
    buy(customer, latte.id)
    review(customer, latte.id)
    assert review(customer, latte.id).status_code == 409


def test_rating_must_be_between_1_and_5(customer, latte):
    """Validation rejects out-of-range ratings."""
    buy(customer, latte.id)
    assert review(customer, latte.id, rating=6).status_code == 422


def test_review_without_comment_has_no_comment_field(customer, latte, mongo_db):
    """Semi-structured data: the comment field only exists when one was written."""
    buy(customer, latte.id)
    review(customer, latte.id, comment=None)
    assert "comment" not in mongo_db.reviews.find_one()


def test_average_rating_across_customers(customer, latte):
    """The aggregation pipeline averages every customer's rating."""
    buy(customer, latte.id)
    review(customer, latte.id, rating=4)
    switch_to_eve(customer)
    buy(customer, latte.id)
    review(customer, latte.id, rating=5)

    summary = customer.get(f"/api/v1/products/{latte.id}/reviews").json()
    assert summary["review_count"] == 2
    assert summary["average_rating"] == 4.5


def test_helpful_votes_count_once_and_not_on_own_review(customer, latte):
    """Each user can vote once on others' reviews, but never on their own."""
    buy(customer, latte.id)
    review_id = review(customer, latte.id).json()["id"]
    assert customer.post(f"/api/v1/reviews/{review_id}/helpful").status_code == 400

    switch_to_eve(customer)
    customer.post(f"/api/v1/reviews/{review_id}/helpful")
    customer.post(f"/api/v1/reviews/{review_id}/helpful")
    summary = customer.get(f"/api/v1/products/{latte.id}/reviews").json()
    assert summary["reviews"][0]["helpful_votes"] == 1


def test_invalid_review_id_returns_404(customer):
    """A badly formed review ID is handled cleanly rather than crashing."""
    assert customer.post("/api/v1/reviews/not-a-real-id/helpful").status_code == 404