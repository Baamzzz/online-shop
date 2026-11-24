"""Customers who bought this also bought' recommendations.

compute_all() reads order history from Postgres, counts which products are bought together,
and stores the top matches for each product in MongoDB, ready for fast reads:
    {"_id": <product id>, "product_ids": [4, 2, 7], "updated_at": ...}
It runs from the CLI for now, and nightly as a cloud function in Stage 8.
"""
from collections import Counter, defaultdict
from datetime import UTC, datetime

from pymongo.database import Database
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import OrderItem, Product


def compute_all(db: Session, mongo: Database, per_product: int = 4) -> int:
    """Rebuild every product's recomendations. Returns how many products got some."""
    # Group the products in each order: {order_id: {product_id, ...}}
    by_order: defaultdict[int, set[int]] = defaultdict(set)
    for order_id, product_id in db.execute(select(OrderItem.order_id, OrderItem.product_id)):
        by_order[order_id].add(product_id)

    # Count how often each pair of products appears in the same order
    bought_with: defaultdict[int, Counter[int]] = defaultdict(Counter)
    for products in by_order.values():
        for product in products:
            for other in products:
                if other != product:
                    bought_with[product][other] += 1

    now = datetime.now(UTC)
    for product_id, counts in bought_with.items():
        top = [other for other, _ in counts.most_common(per_product)]
        mongo.recommendations.replace_one(
            {"_id": product_id}, {"product_ids": top, "updated_at": now}, upsert=True
        )
    return len(bought_with)


def for_product(db: Session, mongo: Database, product: Product, limit: int = 4) -> list[Product]:
    """Products to show under 'Customers also bought', falling back to the same category."""
    doc = mongo.recommendations.find_one({"_id": product.id})
    ids = doc["product_ids"] if doc else []

    recommended: list [Product] = []
    if ids:
        query = select(Product).where(Product.id.in_(ids), Product.is_active.is_(True))
        found = {p.id: p for p in db.scalars(query)}
        recommended = [found[i] for i in ids if i in found] # Keep "most bought together" order

    if not recommended and product.category_id is not None:
        # New products have no order history yet, so suggest other from the same category
        query = (
            select(Product)
            .where(
                Product.category_id == product.category_id,
                Product.id != product.id,
                Product.is_active.is_(True),
            )
            .limit(limit)
        )
        recommended = list(db.scalars(query))

    return recommended[:limit]