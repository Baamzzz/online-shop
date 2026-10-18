"""Customer order routes and promo code checking."""
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbSession
from app.core.rate_limit import limiter
from app.models import Order
from app.schemas.order import OrderCreate, OrderOut, PromoCheck, PromoCheckOut
from app.services.orders import OrderError, get_valid_promo, place_order

router = APIRouter(tags=["orders"])


@router.post("/orders", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(data: OrderCreate, user: CurrentUser, db: DbSession) -> Order:
    """Place an order for the logged-in customer."""
    try:
         return place_order(db, user, data.items, data.promo_code)
    except OrderError as error:
         raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from None


@router.get("/orders", response_model=list[OrderOut])
def list_my_orders(user: CurrentUser, db: DbSession) -> list[Order]:
     """List the logged-in customer's own orders, newest first."""
     query = (
          select(Order)
          .where(Order.user_id == user.id)
          .options(selectinload(Order.items))
          .order_by(Order.id.desc())
     )
     return list(db.scalars(query))


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_my_order(order_id: int, user: CurrentUser, db: DbSession) -> Order:
      """Get one of the customer's own orders."""
      order = db.get(Order, order_id)
      # Someone else's order gets the same 404 as a missing one (prevents IDOR and ID probing)
      if order is None or order.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
      return order


@router.post("/promo/validate", response_model=PromoCheckOut)
@limiter.limit("10/minute")
def validate_promo(request: Request, data: PromoCheck, db: DbSession) -> PromoCheckOut:
    """Check a promo code at checkout. Rate limited so codes can't be guessed by brute force."""
    try:
        promo = get_valid_promo(db, data.code)
    except OrderError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from None
    return PromoCheckOut(code=promo.code, discount_percent=promo.discount_percent)