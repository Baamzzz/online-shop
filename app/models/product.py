"""Product catalogue models: categories and products."""
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Category(Base):
    """A group of producats, e.g. 'Drinks' or 'Pastries'."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)

    products: Mapped[list["Product"]] = relationship(back_populates="category")



class Product(Base):
    """An item for sale. Flexible extra details (Allergens etc.) will live in MongoDB."""

    __tablename__= "products"
    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_product_price_not_negative"),
        CheckConstraint("stock >= 0", name="ck_product_stock_not_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[str | None] = mapped_column(String(500))
    # Numeric rather than float, so money never suffers rounding errors
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    stock: Mapped[int] = mapped_column(default=0)
    image_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(default=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))

    category: Mapped[Category | None] = relationship(back_populates="products")