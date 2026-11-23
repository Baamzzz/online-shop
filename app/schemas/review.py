"""Pydantic schemas for product reviews."""
from datetime import datetime

from pydantic import BaseModel, Field


class ReviewIn(BaseModel):
    """What a customer sends to review a product. THe comment is optional."""

    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class ReviewOut(BaseModel):
    """A review as shows on the product page."""

    id: str
    product_id: int
    author_name: str
    rating: int
    comment: str | None
    helpful_votes: int
    created_at: datetime


class ReviewSummary(BaseModel):
    """A product's average rating, review count and latest reviews."""

    average_rating: float | None
    review_count: int
    reviews: list[ReviewOut]