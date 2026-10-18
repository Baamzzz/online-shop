"""Admin-only routes. Every route in this router requires the admin role."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import DbSession, require_admin
from app.models import Category, Order, Product, PromoCode, User
from app.schemas.order import (
    OrderOut,
    OrderStatusUpdate,
    PromoCodeCreate,
    PromoCodeOut,
)
from app.schemas.product import (
    CategoryCreate,
    CategoryOut,
    ProductCreate,
    ProductOut,
    ProductUpdate,
)
from app.schemas.user import UserOut

# Applying require_admin at router level makes every route here admin-only by default,
# so a new admin route can't accidentally be left unprotected
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])



def _get_product_or_404(db: Session, product_id: int) -> Product:
    """Fetch a product (active or not) or raise 404."""
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    return product


def _check_category_exists(db: Session, category_id: int | None) -> None:
    """Reject a category_id that doesn't exist with a clear 400 error."""
    if category_id is not None and db.get(Category, category_id) is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Category does not exist")


    
@router.get("/users", response_model=list[UserOut])
def list_users(db: DbSession) -> list[User]:
    """List all user accounts."""
    return list(db.scalars(select(User).order_by(User.id)))

@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(data: CategoryCreate, db: DbSession) -> Category:
    """Create a product category."""
    if db.scalar(select(Category).where(Category.name == data.name)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Category already exists")
    category = Category(name=data.name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category 


@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(data: ProductCreate, db: DbSession) -> Product:
    """Add a new product to the shop."""
    _check_category_exists(db, data.category_id)
    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.patch("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, data: ProductUpdate, db: DbSession) -> Product:
    """Change only the fields sent in the request."""
    product = _get_product_or_404(db, product_id)
    changes = data.model_dump(exclude_unset=True)
    if "category_id" in changes:
        _check_category_exists(db, changes["category_id"])
    for field, value in changes.items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: DbSession) -> None:
    """Soft delete: hide the product from the shop but keep it, so past orders still make sense."""
    product = _get_product_or_404(db, product_id)
    product.is_active = False
    db.commit()

@router.post("/promo-codes", response_model=PromoCodeOut, status_code=status.HTTP_201_CREATED)
def create_promo_code(data: PromoCodeCreate, db: DbSession) -> PromoCode:
    """Create a promo code. Codes are stored in uppercase so matching ignores case."""
    code = data.code.upper()
    if db.scalar(select(PromoCode).where(PromoCode.code == code)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Promo code already exists")
    promo = PromoCode(**data.model_dump(exclude={"code"}), code=code)
    db.add(promo)
    db.commit()
    db.refresh(promo)
    return promo


@router.get("/orders", response_model=list[OrderOut])
def list_all_order(db: DbSession) -> list[Order]:
    """List every order, newest first."""
    query = select(Order).options(selectinload(Order.items)).order_by(Order.id.desc())
    return list(db.scalars(query))

@router.patch("/orders/{order_id}/status", response_model=OrderOut)
def update_order_status(order_id: int, data: OrderStatusUpdate, db: DbSession) -> Order:
    """Move an order to a new status, e.g. paid or completed."""
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    order.status = data.status
    db.commit()
    db.refresh(order)
    return order