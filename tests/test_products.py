"""Tests for the product catalogue and amdin product management."""
from tests.test_auth import login, register

PRODUCTS_URL = "/api/v1/products"
ADMIN_PRODUCTS_URL = "/api/v1/admin/products"


def create_category(client, name="Drinks"):
    """Helper: create a category as admin and return it."""
    return client.post("/api/v1/admin/categories", json={"name": name}).json()


def create_product(client, **overrides):
     """Helper: create a product as admin. Pass keyword arguments to change fields."""
     data = {"name": "Latte", "price": "3.20", "stock": 10} | overrides
     return client.post(ADMIN_PRODUCTS_URL, json=data)


def test_admin_creates_product_and_shop_shows_it(admin_client):
     """A product created by an admin appears in the public catalogue."""
     category = create_category(admin_client)
     assert create_product(admin_client, category_id=category["id"]).status_code == 201

     products= admin_client.get(PRODUCTS_URL).json()
     assert products[0]["name"] == "Latte"
     assert products[0]["category"]["name"] == "Drinks"


def test_customer_cannot_create_products(client):
     """Customers get 403 on admin product routes."""
     register(client)
     login(client)
     assert create_product(client).status_code == 403


def test_negative_price_is_rejected(admin_client):
          """Validation blocks prices of zero or below."""
          assert create_product(admin_client, price="-1,00").status_code == 422


def test_unknown_category_is_rejected(admin_client):
     """A product can't point at a category that doesn't exist."""
     assert create_product(admin_client, category_id=999).status_code == 400


def test_search_filters_by_name(admin_client):
     """The q parameter matches product names, ignoring case."""
     create_product(admin_client, name="Latte")
     create_product(admin_client, name="Croissant")
     results = admin_client.get(PRODUCTS_URL, params={"q": "LAT"}).json()
     assert [p["name"] for p in results] == ["Latte"]


def test_patch_changes_only_sent_fields(admin_client):
     """Updating the price leaves the other fields untouched."""
     product = create_product(admin_client).json()
     response = admin_client.patch(f"{ADMIN_PRODUCTS_URL}/{product['id']}", json={"price": "3.50"})
     assert response.json()["price"] == "3.50"
     assert response.json()["name"] == "Latte"


def test_delete_product_is_hidden_from_shop(admin_client):
     """Soft-deleted products dissaper from the shop but aren't destroyed."""
     product = create_product(admin_client).json()
     admin_client.delete(f"{ADMIN_PRODUCTS_URL}/{product['id']}")

     assert admin_client.get(f"{PRODUCTS_URL}/{product['id']}").status_code == 404
     assert admin_client.get(PRODUCTS_URL).json() == []
     assert len(admin_client.get(ADMIN_PRODUCTS_URL).json()) == 1