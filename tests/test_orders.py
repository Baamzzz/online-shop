"""Tests for placing order, stock control and promo codes."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.models import Product, PromoCode
from tests.test_auth import LOGIN_URL, PASSWORD, login, register

ORDERS_URL = "/api/v1/orders"


@pytest.fixture
def latte(db_session):
    """A product with 5 in stock."""
    product = Product(name="Latte", price=Decimal("3.20"), stock=5)
    db_session.add(product)
    db_session.commit()
    return product


@pytest.fixture
def customer(client):
    """A test client logged in as a customer."""
    register(client)
    login(client)
    return client

def add_promo(db_session, **fields):
    """Helper: save a promo code straight to the test database."""
    db_session.add(PromoCode(**fields))
    db_session.commit()


def place(client, product_id, quantity=1, promo_code=None):
    """Helper: place a single-line order through the API."""
    payload = {"items": [{"product_id": product_id, "quantity": quantity}]}
    if promo_code:
        payload["promo_code"] = promo_code
    return client.post(ORDERS_URL, json=payload)


def test_order_totals_and_stock_reduction(customer, latte, db_session):
    """An order is priced from the database and reduces stock."""
    response = place(customer, latte.id, quantity=2)
    assert response.status_code == 201
    assert response.json()["total"] == "6.40"
    db_session.refresh(latte)
    assert latte.stock == 3


def test_client_cannot_set_its_own_price(customer, latte):
    """A price sent by the client is ignored; the database price is charged."""
    payload = {"items": [{"product_id": latte.id, "quantity": 1, "unit_price": "0.01"}]}
    assert customer.post(ORDERS_URL, json=payload).json()["total"] == "3.20"


def test_not_enough_stock_leaves_stock_unchanged(customer, latte, db_session):
    """A rejected order must not change stock."""
    assert place(customer, latte.id, quantity=6).status_code == 400
    db_session.refresh(latte)
    assert latte.stock == 5


def test_promo_code_applies_discount(customer, latte, db_session):
    """A valid code (any case) tales the right percentage off."""
    add_promo(db_session, code="SAVE10", discount_percent=10)
    body = place(customer, latte.id, quantity=2, promo_code="save10").json()
    assert body["subtotal"] == "6.40"
    assert body["discount"] == "0.64"
    assert body["total"] == "5.76"


def test_expired_promo_is_rejected(customer, latte, db_session):
    """Codes past their expiry date can't be used."""
    yesterday = datetime.now(UTC) - timedelta(days=1)
    add_promo(db_session, code="OLDCODE", discount_percent=10, expires_at=yesterday)
    assert place(customer, latte.id, promo_code="OLDCODE").status_code == 400


def test_promo_usage_limit_is_enforced(customer, latte, db_session):
    """A single-use code works once, then is rejected."""
    add_promo(db_session, code="ONCE", discount_percent=10, usage_limit=1)
    assert place(customer, latte.id, promo_code="ONCE").status_code == 201
    assert place(customer, latte.id, promo_code="ONCE").status_code == 400


def test_customers_cannot_see_other_customers_orders(client, latte):
    """Another customer gets 404 for an order that isn't theirs (no IDOR)."""
    register(client)
    login(client)
    order_id = place(client, latte.id).json()["id"]
    client.post("/api/v1/auth/logout")

    register(client, email="eve@example.com")
    client.post(LOGIN_URL, json={"email": "eve@example.com", "password": PASSWORD})
    assert client.get(f"{ORDERS_URL}/{order_id}").status_code == 404

def test_empty_order_is_rejected(customer):
    """An order must have at least one item."""
    assert customer.post(ORDERS_URL, json={"items": []}).status_code == 422


def test_ordering_requires_login(client, latte):
    """Anonymous users can't place orders."""
    assert place(client, latte.id).status_code == 401


def test_multi_item_order_charges_each_line_correctly(customer, latte, db_session):
    """Each product's own quantity is used for its stock and price."""
    croissant = Product(name="Croissant", price=Decimal("2.50"), stock=5)
    db_session.add(croissant)
    db_session.commit()

    payload = {
        "items": [
            {"product_id": latte.id, "quantity": 1},
            {"product_id": croissant.id, "quantity": 3},
        ]
    }
    response = customer.post(ORDERS_URL, json=payload)
    assert response.json()["total"] == "10.70"  # 3.20 + (3 x 2.50)

    db_session.refresh(latte)
    db_session.refresh(croissant)
    assert latte.stock == 4
    assert croissant.stock == 2