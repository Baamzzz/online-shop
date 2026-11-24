"""Tests for 'customers who bought this also bought' recommendations."""
from decimal import Decimal

import pytest

from app.models import Category, Product
from app.services.recommendations import compute_all


@pytest.fixture
def menu(db_session):
    """Four products in the same category."""
    drinks = Category(name="Drinks")
    products = {
        name: Product(name=name, price=Decimal("2.00"), stock=20, category=drinks)
        for name in ["Latte", "Croissant", "Muffin", "Tea"]
    }
    db_session.add_all(products.values())
    db_session.commit()
    return products


def order(client, *product_ids):
    """Helper: place one order containing one of each given product."""
    items = [{"product_id": pid, "quantity": 1} for pid in product_ids]
    client.post("/api/v1/orders", json={"items": items})


def names(client, product_id):
    """Helper: the names of a product's recommendations, in order."""
    response = client.get(f"/api/v1/products/{product_id}/recommendations")
    return [p["name"] for p in response.json()]


def test_most_often_bought_together_comes_first(customer, menu, db_session, mongo_db):
    """Croissant was bought with Latte twice and Muffin once, so Croissant ranks first."""
    latte, croissant, muffin = menu["Latte"], menu["Croissant"], menu["Muffin"]
    order(customer, latte.id, croissant.id)
    order(customer, latte.id, croissant.id)
    order(customer, latte.id, muffin.id)

    compute_all(db_session, mongo_db)
    assert names(customer, latte.id) == ["Croissant", "Muffin"]


def test_products_without_history_fall_back_to_same_category(client, menu):
    """With no orders yet, other products from the same category are suggested."""
    recommended = names(client, menu["Tea"].id)
    assert "Tea" not in recommended
    assert len(recommended) == 3


def test_hidden_products_are_never_recommended(customer, menu, db_session, mongo_db):
    """A product removed from the shop disappears from recommendations straight away."""
    latte, croissant = menu["Latte"], menu["Croissant"]
    order(customer, latte.id, croissant.id)
    compute_all(db_session, mongo_db)

    croissant.is_active = False
    db_session.commit()
    assert "Croissant" not in names(customer, latte.id)