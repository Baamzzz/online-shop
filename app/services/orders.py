"""Order and pormo code business logic: stock checks, pricing and discounts."""
from collections import Counter
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Order, OrderItem, Product, PromoCode, User
from app.schemas.order import OrderItemIn

PENNY = Decimal("0.01")

class OrderError(Exception):
    """A business rule stopped the order, e.g. out of stock or an invalid promo code."""



def _as_utc(moment: datetime) -> datetime:
    """SQLite returns datetimes without a timezone; treat those as UTC."""
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def get_valid_promo(db: Session, code: str) -> PromoCode:
    """Return as active, unexpired promo code with uses left, or raise OrderError."""
    promo = db.scalar(select(PromoCode).where(PromoCode.code == code.upper()))
    if promo is None or not promo.is_active:
        raise OrderError("Promo code is not valid")
    if promo.expires_at and _as_utc(promo.expires_at) < datetime.now(UTC):
        raise OrderError("Promo code has expired")
    if promo.usage_limit is not None and promo.times_used >= promo.usage_limit:
        raise OrderError("Promo code has reached its usage limit")
    return promo


def place_order(
        db: Session, user: User, items: list[OrderItemIn], promo_code: str | None
) -> Order:
    """Create an order in one transaction: check stock, price from the DB, discount, reduce stock."""
    promo = get_valid_promo(db, promo_code) if promo_code else None


    # Merge repeated lines for the same product, e.g. two "1 x Latte" Lines become "2 x Latte"
    quantities: Counter[int] = Counter()
    for item in items:
        quantities[item.product_id] += item.quantity


    # Lock these product rown until commit, so two orders at the same moment
    # can't both buy the last item (ignored by SQLite in tests, enforced by postgres)
    products = db.scalars(
        select(Product).where(Product.id.in_(quantities)).with_for_update()
    ).all()
    products_by_id = {product.id: product for product in products}

    # First pass: check everything before changing anything
    for product_id, quantity in quantities.items():
        product = products_by_id.get(product_id)
        if product is None or not product.is_active:
            raise OrderError(f"Product {product_id} is not available")
        if product.stock < quantity:
            raise OrderError(f"Not enough stock for {product.name}")


    # Second pass: every check passed, so build the order and reduce stock
    order = Order(user=user)
    subtotal = Decimal("0.00")
    for product_id, quantity in quantities.items():
        product = products_by_id[product_id]
        product.stock -= quantity
        # unit_price is copied now, so the order stays corrent if the price changes later
        order.items.append(OrderItem(product=product, quantity=quantity, unit_price=product.price))
        subtotal += product.price * quantity

    discount = Decimal("0.00")
    if promo is not None:
        discount = (subtotal * promo.discount_percent / 100).quantize(PENNY, rounding=ROUND_HALF_UP)
        promo.times_used += 1
        order.promo_code = promo


    order.subtotal = subtotal
    order.discount = discount
    order.total = subtotal - discount
    db.add(order)
    db.commit() # Stock, promo usage and the order are all saved together, or not at all
    db.refresh(order)
    return order