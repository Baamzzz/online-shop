"""Tests for the MongoDB shopping cart and checkout."""
from tests.test_auth import LOGIN_URL, PASSWORD, register

CART_URL = "/api/v1/cart"


def add(client, product_id, quantity=1):
    """Helper: set a product's quantity in the cart."""
    return client.put(f"{CART_URL}/items", json={"product_id": product_id, "quantity": quantity})



def test_cart_shows_live_names_prices_and_subtotal(customer, latte):
    """Cart lines are filled in with product details from Postgres."""
    add(customer, latte.id, quantity=2)
    cart = customer.get(CART_URL).json()
    assert cart["items"][0]["name"] == "Latte"
    assert cart["items"][0]["line_total"] == "6.40"
    assert cart["subtotal"] == "6.40"


def test_cart_stores_ids_and_quantities_but_no_prices(customer, latte, mongo_db):
    """The MongoDB document never holds prices, so they can't be tampered with."""
    add(customer, latte.id, quantity=2)
    document = mongo_db.carts.find_one()
    assert document["items"] == [{"product_id": latte.id, "quantity": 2}]


def test_adding_same_product_replaces_quantity(customer, latte):
    """Setting a product again updates its quantity rather than adding a second line."""
    add(customer, latte.id, quantity=3).json()
    cart = add(customer, latte.id, quantity=3).json()
    assert len(cart["items"]) == 1
    assert cart["items"][0]["quantity"] == 3


def test_unknown_product_is_rejected(customer):
    """You can't add a product that does not exist."""
    assert add(customer, 999).status_code == 404


def test_cannot_add_more_than_stock(customer, latte):
    """Quantities above the available stock are rejected."""
    assert add(customer, latte.id, quantity=6).status_code == 400


def test_remove_item(customer, latte):
    """Removing a product empties that line."""
    add(customer, latte.id)
    assert customer.delete(f"{CART_URL}/items/{latte.id}").json()["items"] == []


def test_cart_requires_login(client):
    """Anonymous users don't have a cart."""
    assert client.get(CART_URL).status_code == 401


def test_carts_are_private_to_each_user(client, latte):
    """One customer's cart is never visible to another."""
    register(client)
    client.post(LOGIN_URL, json={"email": "alice@example.com", "password": PASSWORD})
    add(client, latte.id)
    client.post("/api/v1/auth/logout")

    register(client, email="eve@example.com")
    client.post(LOGIN_URL, json={"email": "eve@example.com", "password": PASSWORD})
    assert client.get(CART_URL).json()["items"] == []


def test_checkout_creates_order_and_empties_cart(customer, latte, db_session):
    """Checkout moves the cart into a Postgres order and reduces stock."""
    add(customer, latte.id, quantity=2)
    response = customer.post(f"{CART_URL}/checkout", json={})
    assert response.status_code == 201
    assert response.json()["total"] == "6.40"

    assert customer.get(CART_URL).json()["items"] == []
    db_session.refresh(latte)
    assert latte.stock == 3


def test_checkout_with_empty_cart_is_rejected(customer):
    """You can't check out with nothing in the cart."""
    assert customer.post(f"{CART_URL}/checkout", json={}).status_code == 400