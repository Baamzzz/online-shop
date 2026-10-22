"""Shopping cart routes. Every route works on the logged in users own cart."""
from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUser, DbSession, MongoDB
from app.models import Order, Product
from app.schemas.cart import CartItemIn, CartOut, CheckoutIn
from app.schemas.order import OrderItemIn, OrderOut
from app.services import cart as cart_service
from app.services.orders import OrderError, place_order

router = APIRouter(prefix="/cart", tags=["cart"])

@router.get("", response_model=CartOut)
def view_cart(user: CurrentUser, db: DbSession, mongo: MongoDB) -> CartOut:
    """Show the cart with live prices and a running total."""
    return cart_service.build_cart_view(db, cart_service.get_items(mongo, user.id))


@router.put("/items", response_model=CartOut)
def set_cart_item(data: CartItemIn, user: CurrentUser, db: DbSession, mongo: MongoDB) -> CartOut:
    """Add a product or change its quantity."""
    product = db.get(Product, data.product_id)
    if product is None or not product.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    if data.quantity > product.stock:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Only {product.stock} in stock")
    cart_service.set_quantity(mongo, user.id, data.product_id, data.quantity)
    return cart_service.build_cart_view(db, cart_service.get_items(mongo, user.id))

@router.delete("/items/{product_id}", response_model=CartOut)
def remove_cart_item(product_id: int, user: CurrentUser, db: DbSession, mongo: MongoDB) -> CartOut:
    """Remove one product form the cart."""
    cart_service.remove_item(mongo, user.id, product_id)
    return cart_service.build_cart_view(db, cart_service.get_items(mongo, user.id))


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def clear_cart(user: CurrentUser, mongo: MongoDB) -> None:
    """Empty cart."""
    cart_service.clear(mongo, user.id)


@router.post("/checkout", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def checkout(data: CheckoutIn, user: CurrentUser, db: DbSession, mongo: MongoDB) -> Order:
    """Turn the cart (MongoDB) into an order (Postgres), then empty the cart."""
    raw_items = cart_service.get_items(mongo, user.id)
    if not raw_items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your cart is empty")

    items = [OrderItemIn(**item) for item in raw_items]
    try:
        order = place_order(db, user, items, data.promo_code)
    except OrderError as error:
        # The cart is kept, so the customer can fix the problem and try again
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from None


    cart_service.clear(mongo, user.id)
    return order