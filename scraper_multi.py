"""
scraper_multi.py
Scraper multi plateforme
"""

from playwright.sync_api import sync_playwright
from database import SessionLocal, Product
from scoring_ai import score_with_local_ai
import random
from datetime import datetime


def insert_product(session, title, platform, price, affiliate_url=""):

    supplier_price = round(price * random.uniform(0.35, 0.55), 2)

    margin = (price - supplier_price) / supplier_price

    score = score_with_local_ai(
        title=title,
        price=price,
        supplier_price=supplier_price
    )

    product = Product(
        title=title,
        platform=platform,
        price=price,
        supplier_price=supplier_price,
        margin=margin,
        sales=random.randint(10, 1000),
        reviews=random.randint(0, 500),
        rating=random.uniform(3.5, 5),
        trend_score=random.uniform(0.4, 0.9),
        opportunity_score=score,
        affiliate_url=affiliate_url,
        scraped_at=datetime.utcnow()
    )

    session.add(product)


def main():

    session = SessionLocal()

    try:

        with sync_playwright() as p:

            browser = p.chromium.launch(headless=True)

            page = browser.new_page()

            page.goto("https://example.com")

            insert_product(
                session,
                "Example product",
                "Example",
                25.99
            )

            browser.close()

        session.commit()

    except Exception as e:

        session.rollback()

        print("Scraper error", e)

    finally:

        session.close()