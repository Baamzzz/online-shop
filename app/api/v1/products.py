"""Public product catalogue routes: anyone can browse."""
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import DbSession
from app.models import Product
from app.schemas.product import ProductOut

router = APIRouter(tags=["products"])


@router.get("/products", response_model=list[ProductOut])
def list_products(
    db: DbSession,
    q: str | None = Query(default=None, max_length= 100, description="Search by name"),
    category_id: int | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[Product]:
    """List active products, with optional search, category filter and pagination."""
    # selecinload fetches every product's category in one extra query,
    # instead of one query per product (the "N+1 query" problem)
    query = (
        select(Product)
        .options(selectinload(Product.category))
        .where(Product.is_active.is_(True))
    )
    if q:
        # SQLAlchemy sends q as a bound parameter, so user input can't inject SQL
        query = query.where(Product.name.ilike(f"%{q}%"))
    if category_id is not None:
        query = query.where(Product.category_id == category_id)
    query = query.order_by(Product.name).limit(limit).offset(offset)
    return list(db.scalars(query))



@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: DbSession) -> Product:
    """Get one active product by ID."""
    product = db.get(Product, product_id, options=[selectinload(Product.category)])
    if product is None or not product.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    return product