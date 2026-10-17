"""Pydantic schemas for categories and products."""
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    """Data needed to create a category."""

    name: str = Field(min_length=1, max_length=50)
                      

class CategoryOut(BaseModel):
    """A category as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ProductCreate(BaseModel):
    """Data needed to create a product. Validation blocks bad prices and stock."""

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    stock: int = Field(default=0, ge=0)
    image_url: str | None = Field(default=None, max_length=500)
    category_id: int | None = None


class ProductUpdate(BaseModel):
    """Every field is optional: only the fields sent are changed (PATCH)."""

    name : str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    stock: int | None = Field(default=None, ge=0)
    image_url: str | None = Field(default=None, max_length=500)
    category_id: int | None = None
    is_active: bool | None = None


class ProductOut(BaseModel):
    """A product as returned by the API, including its category."""

    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    description: str | None
    price: Decimal
    stock: int
    image_url: str | None
    is_active: bool
    category: CategoryOut | None