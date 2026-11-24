"""Pydantic schemas for the admin analytics view."""
from pydantic import BaseModel


class PopularProduct(BaseModel):
    """A product and how many times it was viewed."""

    product_id: int
    name: str
    views: int


class SearchTerm(BaseModel):
    """A search term and how many times it was used."""

    query: str
    count: int


class AnalyticsOut(BaseModel):
    """Shopper behaviour over the last N days."""

    days: int
    most_viewed: list[PopularProduct]
    top_searches: list[SearchTerm]