"""Pydantic schemas for the shopping cart."""
from decimal import Decimal

from pydantic import BaseModel, Field


class CartItemIn(BaseModel):
    """Set the qunatity of one product in the cart."""

    product_id: int
    quantity: int = Field(ge=1, le=50)


class CartLineOut(BaseModel):
    """One cart line with live product details from Postgres."""

    product_id: int
    name: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal


class CartOut(BaseModel):
    """The whole cart and its running total."""

    items: list[CartLineOut]
    subtotal: Decimal


class CheckoutIn(BaseModel):
    """Optional promo code applied at checkout."""

    promo_code: str | None = Field(default=None, max_length=30)