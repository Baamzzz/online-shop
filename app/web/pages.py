"""Web pages (HTML). Pages read data directly using the existing services; actions 
such as logging in or adding to the cart are sent from the browser to the JSON API by static/app.js."""
from pathlib import Path

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.v1 import admin as admin_api
from app.core.deps import DbSession, MongoDb, OptionalUser
from app.models import Category, Order, OrderItem, Product
from app.services import cart as cart_service
from app.services import events, recommendations
from app.services import reviews as review_service

# Jinja2 escapes everything it inserts into HTML by default, which protects against XSS
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")

# include_in_schema=False keeps these HTML pages out of the API docs at /docs
router = APIRouter(include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    db: DbSession,
    mongo: MongoDb,
    user: OptionalUser,
    q: str | None = Query(default=None, max_length=100),
    category_id: str | None = None,
):
    """Shop front page: browse and search products."""
    # The category dropdown sends "" for "All categories", so convert carefully
    category = int(category_id) if category_id and category_id.isdigit() else None

    query = (
        select(Product)
        .options(selectinload(Product.category))
        .where(Product.is_active.is_(True))
    )
    if q and q.strip():
        events.track(mongo, "search", user.id if user else None, query=q.strip().lower())
        query = query.where(Product.name.ilike(f"%{q.strip()}%"))
    if category is not None:
        query = query.where(Product.category_id == category)

    context =  {
        "user": user,
        "q": q,
        "category_id": category,
        "products": db.scalars(query.order_by(Product.name)).all(),
        "categories": db.scalars(select(Category).order_by(Category.name)).all(),
    }
    return templates.TemplateResponse(request, "home.html", context)


@router.get("/products/{product_id}", response_class=HTMLResponse)
def product_page(
    product_id: int, request: Request, db: DbSession, mongo: MongoDb, user: OptionalUser
):
    """Product page with reviews and 'customers also bought'."""
    product = db.get(Product, product_id, options=[selectinload(Product.category)])
    if product is None or not product.is_active:
        return templates.TemplateResponse(
            request, "not_found.html", {"user": user}, status_code=404
        )

    events.track(mongo, "product_view", user.id if user else None, product_id=product.id)
    context = {
        "user": user,
        "product": product,
        "reviews": review_service.product_reviews(mongo, product.id),
        "recommendations": recommendations.for_product(db, mongo, product),
    }
    return templates.TemplateResponse(request, "product.html", context)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user: OptionalUser, registered: bool = False):
    """Login form. ?registered=1 shows a 'you can log in now' message after sign-up."""
    return templates.TemplateResponse(
        request, "login.html", {"user": user, "registered": registered}
    )


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, user: OptionalUser):
    """Sign-up form."""
    return templates.TemplateResponse(request, "register.html", {"user": user})

def _login_redirect() -> RedirectResponse:
    """Send visitores who aren't logged in to the login page."""
    return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/cart", response_class=HTMLResponse)
def cart_page(request: Request, db: DbSession, mongo: MongoDb, user: OptionalUser):
    """The customer's cart, with quantity controls and checkout."""
    if user is None:
        return _login_redirect()
    cart = cart_service.build_cart_view(db, cart_service.get_items(mongo, user.id))
    return templates.TemplateResponse(request, "cart.html", {"user": user, "cart": cart})


@router.get("/orders", response_class=HTMLResponse)
def orders_page(request: Request, db: DbSession, user: OptionalUser, mongo: MongoDb, placed: bool = False):
    """The customer's order history. ?placed=1 shows a thank-you message after checkout."""
    if user is None:
        return _login_redirect()
    query = (
        select(Order)
        .where(Order.user_id == user.id)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .order_by(Order.id.desc())
    )
    context = {"user": user, "orders": db.scalars(query).all(), "placed": placed}
    return templates.TemplateResponse(request, "orders.html", context)

@router.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request, db: DbSession, mongo: MongoDb, user: OptionalUser):
    """Admin dashboard: analytics, low stock, recent orders and adding products."""
    if user is None:
        return _login_redirect()
    if user.role != "admin":
        # Customers see the normal not-found page, so the admin area isn't advertised.
        # The real protection is require_admin on every admin API route.
        return templates.TemplateResponse(
            request, "not_found.html", {"user": user}, status_code=404
        )

    low_stock = select(Product).where(Product.is_active.is_(True), Product.stock <=5)
    recent_orders = (
        select(Order).options(selectinload(Order.items)).order_by(Order.id.desc()).limit(10)
    )
    context = {
        "user": user,
        # Reuses the analytics API function, so the numbers always match /api/v1/admin/analytics
        "analytics": admin_api.analytics(db, mongo, days=7),
        "low_stock": db.scalars(low_stock.order_by(Product.stock)).all(),
        "recent_orders": db.scalars(recent_orders).all(),
        "categories": db.scalars(select(Category).order_by(Category.name)).all(),
    }
    return templates.TemplateResponse(request, "admin.html", context)