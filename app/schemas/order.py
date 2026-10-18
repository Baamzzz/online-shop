"""Pydantic schemas for orders and promo codes."""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models import OrderStatus


class OrderItemIn(BaseModel):
    """One line of a new order: only the product and quantity. Prices comem from database."""

    product_id: int
    quantity: int = Field(ge=1, le=50)


class OrderCreate(BaseModel):
    """What the customer sends to place an order."""

    items: list[OrderItemIn] = Field(min_length=1, max_length=50)
    promo_code: str | None = Field(default=None, max_length=30)


class OrderItemOut(BaseModel):
    """One line of an order, as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    product_id: int
    quantity: int
    unit_price: Decimal


class OrderOut(BaseModel):
    """An order with its lines and totals."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: OrderStatus
    subtotal: Decimal
    discount: Decimal
    total: Decimal
    created_at: datetime
    items: list[OrderItemOut]


class OrderStatusUpdate(BaseModel):
    """Admin requesti to move an order to a new status."""

    status: OrderStatus


class PromoCodeCreate(BaseModel):
    """Admin request to create a promo code. Letters and numbers only."""

    code: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9]+$")
    discount_percent: int = Field(ge=1, le=100)
    expires_at: datetime | None = None
    usage_limit: int | None = Field(default=None, ge=1)


class PromoCodeOut(BaseModel):
    """A promo code as shown to admins."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    discount_percent: int
    expires_at: datetime | None
    usage_limit: int | None
    times_used: int
    is_active: bool


class PromoCheck(BaseModel):
    """A code the customer wants to check at checkout."""

    code: str = Field(max_length=30)


class PromoCheckOut(BaseModel):
    """Result of a succesful promo code check."""

    code: str
    discount_percent: int