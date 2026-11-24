"""Public product catalogue routes: anyone can browse."""
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import DbSession, MongoDb, OptionalUser
from app.models import Product
from app.schemas.product import ProductOut
from app.services import events
from app.services import Recommendations

router = APIRouter(tags=["products"])


@router.get("/products", response_model=list[ProductOut])
def list_products(
    db: DbSession,
    mongo: MongoDb,
    user: OptionalUser,
    q: str | None = Query(default=None, max_length=100, description="Search by name"),
    category_id: int | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[Product]:
    """List active products, with optional search, category filter and pagination."""
    if q:
        # Lowercased and trimmed so "Latte" and " Latte " count as the same search
        events.track(mongo, "search", user.id if user else None, query=q.strip().lower())
    # selecintload fetches every product's category in one extra query,
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
def get_product(product_id: int, db: DbSession, mongo: MongoDb, user: OptionalUser) -> Product:
    """Get one active product by ID."""
    product = db.get(Product, product_id, options=[selectinload(Product.category)])
    if product is None or not product.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    events.track(mongo, "product_view", user.id if user else None, product_id=product.id)
    return product


@router.get("/products/{product_id}/recommendations", response_model=list[ProductOut])
def get_recommendations(product_id: int, db: DbSession, mongo: MongoDb) -> list[Product]:
    """'Customers who bought this also bought' for a product page."""
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    return Recommendations.for_product(db, mongo, product)