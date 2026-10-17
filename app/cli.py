"""Command-line admin tools. 

Usage:
     python -m app.cli 
     make-admin someone@example.com
"""
import argparse
import sys
from decimal import Decimal

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Category, Product, User

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

def main() -> None:
    """Parse the command line and run the chosen command."""
    parser = argparse.ArgumentParser(description="Online Shop admin tools")
    commands = parser.add_subparsers(dest="command", required=True)

    make_admin_cmd = commands.add_parser("make-admin", help="Give a user the admin role")
    make_admin_cmd.add_argument("email")
    commands.add_parser("seed", help="Add sample categories and products")

    args = parser.parse_args()
    if args.command == "make-admin":
        make_admin(args.email)
    elif args.command == "seed":
        seed()

if __name__ == "__main__":
    main()