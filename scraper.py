# backend/scraper.py

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from database import Session, Product
from scoring_ai import score_with_local_ai
from utils import parse_claude_scores

def scrape_books():
    session = Session()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        page = browser.new_page()
        try:
            page.goto("https://books.toscrape.com", timeout=60000)
        except Exception as e:
            print("Erreur de chargement:", e)
            browser.close()
            return

        html = page.content()
        soup = BeautifulSoup(html, "html.parser")

        books = soup.select(".product_pod")

        for book in books:
            title = book.select_one("h3 a")["title"]
            price_text = book.select_one(".price_color").text
            price = float(price_text.replace("£", ""))

            supplier_price = price * 0.4
            margin = (price - supplier_price) / supplier_price

            print(f"Analyse IA pour : {title}")

            opportunity_score = score_with_local_ai(title, price, supplier_price)

            print(f"⚡ Score IA : {opportunity_score}")

            product = Product(
                title=title,
                price=price,
                supplier_price=supplier_price,
                margin=margin,
                opportunity_score=opportunity_score
            )
            session.add(product)

        browser.close()

    session.commit()
    session.close()
    print("Scraping + scoring terminés")

if __name__ == "__main__":
    scrape_books()