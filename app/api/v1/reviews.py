"""Product review routes. Anyone can read reviews; only verified buyers can write them."""
from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUser, DbSession, MongoDB
from app.models import Product
from app.schemas.review import ReviewIn, ReviewOut, ReviewSummary
from app.services import reviews as review_service
from app.services.reviews import ReviewError

router = APIRouter(tags=["reviews"])


@router.get("/products/{product_id}/reviews", response_model=ReviewSummary)
def list_reviews(product_id: int, mongo: MongoDB) -> ReviewSummary:
    """A product's average rating, review count and newest reviews."""
    return review_service.product_reviews(mongo, product_id)


@router.post(
    "/products/{product_id}/reviews",
    response_model=ReviewOut,
    status_code=status.HTTP_201_CREATED,
)
def create_review(
    product_id: int, data: ReviewIn, user: CurrentUser, db: DbSession, mongo: MongoDB
) -> ReviewOut:
    """Review a prodcut you have bought."""
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    try:
        return review_service.add_review(db, mongo, user, product_id, data)
    except ReviewError as error:
        raise HTTPException(error.status_code, str(error)) from None


@router.post("/reviews/{review_id}/helpful", status_code=status.HTTP_204_NO_CONTENT)
def vote_helpful(review_id: str, user: CurrentUser, mongo: MongoDB) -> None:
    "Mark someone else's review as helpful."
    try:
        review_service.mark_helpful(mongo, review_id, user.id)
    except ReviewError as error:
        raise HTTPException(error.status_code, str(error)) from None