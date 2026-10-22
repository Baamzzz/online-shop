"""Shhopping cart logic. Carts live in MongoDB as one document per user:

    {"_id": <user id>, "items": [{"product_id": 1, "quantity": 2}],
     "updated_at": <datetime>, "reminder_sent": false}
"""

from datetime import UTC, datetime
from decimal import Decimal

from pymongo.database import Database
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Product
from app.schemas.cart import CartLineOut, CartOut


def get_items(mongo: Database, user_id: int) -> list[dict]:
    """Return the raw cart items (prouct IDs and quantities) for a user."""
    cart = mongo.carts.find_one({"_id": user_id})
    return cart["items"] if cart else []


def _save_items(mongo: Database, user_id: int, items: list[dict]) -> None:
    """Replace the cart's items. upsert=True creates the cart on first use."""
    mongo.carts.update_one(
        {"_id": user_id},
    # updated_at and reminder_sent drive the abandoned-cart reminder (Stage 8)
    {"$set": {"items": items, "updated_at": datetime.now(UTC), "reminder_sent": False}},
    upsert=True,
    )


def set_quantity(mongo: Database, user_id: int, product_id: int, quantity: int) -> None:
    """Add a product to the cart, or replace its quantity if it's already there."""
    items = [i for i in get_items(mongo, user_id) if i["product_id"] != product_id]
    items.append({"product_id": product_id, "quantity": quantity})
    _save_items(mongo, user_id, items)


def remove_item(mongo: Database, user_id: int, product_id: int) -> None:
    """Remove one product from the cart."""
    items = [i for i in get_items(mongo, user_id) if i["product_id"] != product_id]
    _save_items(mongo, user_id, items)


def clear(mongo: Database, user_id: int) -> None:
    """Delete the whole cart, e.g. after a successful checkout."""
    mongo.carts.delete_one({"_id": user_id})


def build_cart_view(db: Session, items: list[dict]) -> CartOut:
    """Combine cart items with live names and prices from Postgres.

    Products that have since been removed from the shop are silently left out.
    """
    quantities = {i["product_id"]: i["quantity"] for i in items}
    products = db.scalars(
        select(Product).where(Product.id.in_(quantities), Product.is_active.is_(True))
    ).all()

    lines = [
        CartLineOut(
            product_id=p.id,
            name=p.name,
            unit_price=p.price,
            quantity=quantities[p.id],
            line_total=p.price * quantities[p.id],
        )
        for p in products
    ]
    subtotal = sum((line.line_total for line in lines), Decimal("0.00"))
    return CartOut(items=lines, subtotal=subtotal)