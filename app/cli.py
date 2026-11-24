"""Command-line admin tools. 

Usage:
     python -m app.cli make-admin someone@example.com
     python -m app.cli seed
     python -m app.cli init-mongo
"""
import argparse
import sys
from decimal import Decimal

from sqlalchemy import select

from app.db.mongo import get_mongo
from app.db.session import SessionLocal
from app.models import Category, Product, User
from app.services.recommendations import compute_all

SAMPLE_MENU = {
    "Drinks": [("Latte", "3.20"), ("Cappuccino", "3.10"), ("Hot Chocolate", "3.40")],
    "Pastries": [("Croissant", "2.50"), ("Pain au Chocolat", "2.80"), ("Cinnamon Bun", "3.00")],
    "Lunch": [("Ham and Cheese Toastie", "4.50"), ("Avocado Toast", "5.20")],
}

def make_admin(email: str) -> None:
    """Give an existing user the admin role."""
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email.lower()))
        if user is None:
            sys.exit(f"No user found with email {email}")
        user.role = "admin"
        db.commit()
        print(f"{email} is now an admin")

def seed() -> None:
    """Add sample categories and products. Does nothing if categories already exist."""
    with SessionLocal() as db:
        if db.scalar(select(Category).limit(1)):
            print("Categories already exist, so skipping the seed")
            return
        for category_name, items in SAMPLE_MENU.items():
            category = Category(name=category_name)
            for name, price in items:
                category.products.append(Product(name=name, price=Decimal(price), stock=50))
            db.add(category)
        db.commit()
        print("Added sample menu")


def init_mongo() -> None:
    """Create MongoDB indexes. Safe to run more than once."""
    mongo = get_mongo()
    # Lets the abandoned-cart job quickly find carts that haven't been updated recently
    mongo.carts.create_index("updated_at")
    # One review per customer per product, enforced by the database as a safety net
    mongo.reviews.create_index([("product_id", 1), ("use_id", 1)], unique=True)
    # Delete events automatically after 90 days: data minimisation (keep only what's needed)
    mongo.events.create_index("created_at", expireAfterSeconds=90 * 24 * 60 * 60)
    # Speeds up the analytics queries, which filter by type and date
    mongo.events.create_index([("type", 1), ("created_at", -1)])
    print("MongoDB indexes created")

def update_recommendations() -> None:
    """Rebuild 'customers also bought' from order history."""
    with SessionLocal() as db:
        count = compute_all(db, get_mongo())
    print(f"Recommendations updated for {count} products")

def main() -> None:
    """Parse the command line and run the chosen command."""
    parser = argparse.ArgumentParser(description="Online Shop admin tools")
    commands = parser.add_subparsers(dest="command", required=True)

    make_admin_cmd = commands.add_parser("make-admin", help="Give a user the admin role")
    make_admin_cmd.add_argument("email")
    commands.add_parser("seed", help="Add sample categories and products")
    commands.add_parser("init-mongo", help="Create MongoDB indexes")
    commands.add_parser("recommendations", help="Rebuild product recommendations")

    args = parser.parse_args()
    if args.command == "make-admin":
        make_admin(args.email)
    elif args.command == "seed":
        seed()
    elif args.command == "init-mongo":
        init_mongo()
    elif args.command == "recommendations":
        update_recommendations()

if __name__ == "__main__":
    main()