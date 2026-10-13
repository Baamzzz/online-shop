"""Tests for the SQL database models and their constraints."""
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Category, Order, OrderItem, OrderStatus, Product, User


def make_user(db, email="test@example.com"):
    """Helper: create and save a user."""
    user = User(email=email, full_name="Test User", password_hash="not-a-real-hash")
    db.add(user)
    db.commit()
    return user

def test_order_links_user_items_and_products(db_session):
    """An order should connect to its user, its items and each item's product."""
    user = make_user(db_session)
    drinks = Category(name="Drinks")
    latte = Product(name="Latte", price=Decimal("3.20"), stock=10, category=drinks)
    order = Order(user=user, subtotal=Decimal("6.40"), total=Decimal("6.40"))
    order.items.append(OrderItem(product=latte, quantity=2, unit_price=latte.price))
    db_session.add(order)
    db_session.commit()

    assert order.status == OrderStatus.PENDING
    assert user.orders[0].items[0].product.name == "Latte"
    assert latte.category.name == "Drinks"


def test_duplicate_email_is_rejected(db_session):
    """Two accounts must not share an email address."""
    make_user(db_session)
    with pytest.raises(IntegrityError):
        make_user(db_session)


def test_negative_stock_is_rejected(db_session):
    """The database's check constraint should block negative stock."""
    db_session.add(Product(name="Broken", price=Decimal("1.00"), stock=-1))
    with pytest.raises(IntegrityError):
        db_session.commit()