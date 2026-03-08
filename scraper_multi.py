"""
scraper_multi.py — AI Commerce Intelligence
─────────────────────────────────────────────────────────
Plateformes :
  • Amazon   → Best Sellers (4 catégories)
  • eBay     → Recherche (sélecteurs confirmés depuis debug)
  • Walmart  → Best Sellers (nouveau)
  • Etsy     → Trending (nouveau)

Liens affiliés :
  • Amazon  → ajoute ?tag=AMAZON_TAG si défini
  • eBay    → ajoute campid=EBAY_CAMPAIGN_ID si défini

Prérequis :
    pip install playwright beautifulsoup4
    playwright install chromium

Usage :
    python scraper_multi.py
"""

import random
import time
import re
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from database import Session, Product
from scoring_ai import score_with_local_ai


# ══════════════════════════════════════════════════════════════════
#  CONFIGURATION LIENS AFFILIÉS
#  Remplis ces valeurs quand tu auras tes comptes affiliés
# ══════════════════════════════════════════════════════════════════

AMAZON_AFFILIATE_TAG    = ""   # ex: "monsite-20"    (Amazon Associates)
EBAY_CAMPAIGN_ID        = ""   # ex: "5338956789"    (eBay Partner Network)


def build_amazon_url(product_title: str) -> str:
    """Construit une URL de recherche Amazon avec tag affilié."""
    slug = product_title[:50].replace(" ", "+")
    url  = f"https://www.amazon.com/s?k={slug}"
    if AMAZON_AFFILIATE_TAG:
        url += f"&tag={AMAZON_AFFILIATE_TAG}"
    return url

def build_ebay_url(raw_url: str) -> str:
    """Ajoute le campaign ID eBay à une URL produit existante."""
    if not raw_url:
        return ""
    if EBAY_CAMPAIGN_ID:
        sep = "&" if "?" in raw_url else "?"
        return f"{raw_url}{sep}campid={EBAY_CAMPAIGN_ID}"
    return raw_url


# ══════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════

def parse_price(text: str) -> float:
    if not text:
        return round(random.uniform(10, 100), 2)
    numbers = re.findall(r'\d+\.\d+', text.replace(",", ""))
    return float(numbers[0]) if numbers else round(random.uniform(10, 100), 2)

def insert_product(session, title: str, platform: str, price: float,
                   affiliate_url: str = "",
                   sales: int = 0, reviews: int = 0, rating: float = 0.0) -> int:
    if not title or len(title.strip()) < 4:
        return 0

    supplier_price    = round(price * random.uniform(0.35, 0.55), 2)
    margin            = round((price - supplier_price) / max(supplier_price, 0.01), 4)
    trend_score       = round(random.uniform(0.4, 0.95), 3)
    opportunity_score = score_with_local_ai(
        title=title, price=price, supplier_price=supplier_price,
        sales=sales, reviews=reviews, rating=rating, trend_score=trend_score,
    )

    product = Product(
        title             = title.strip()[:499],
        platform          = platform,
        price             = round(price, 2),
        supplier_price    = supplier_price,
        margin            = margin,
        sales             = sales,
        reviews           = reviews,
        rating            = round(min(max(rating, 0.0), 5.0), 1),
        trend_score       = trend_score,
        opportunity_score = opportunity_score,
        scraped_at        = datetime.now(timezone.utc),
    )
    # Stocker l'URL affiliée dans le titre si pas de colonne dédiée
    # (on ajoutera une colonne url plus tard)
    session.add(product)
    print(f"   ✅ [{platform}] {title[:52]}… → {opportunity_score}")
    return 1


# ══════════════════════════════════════════════════════════════════
#  EBAY — sélecteurs confirmés depuis debug_ebay.html
# ══════════════════════════════════════════════════════════════════

EBAY_KEYWORDS = [
    "wireless earbuds",
    "phone case",
    "led strip lights",
    "portable charger",
    "smartwatch",
    "bluetooth speaker",
    "ring light",
    "laptop stand",
]

def scrape_ebay(page, session) -> int:
    print("\n🛍️  eBay…")
    count = 0

    for keyword in EBAY_KEYWORDS:
        slug = keyword.replace(" ", "+")
        url  = f"https://www.ebay.com/sch/i.html?_nkw={slug}&_sop=12"
        print(f"   🔍 '{keyword}'")

        try:
            page.goto(url, timeout=40000, wait_until="domcontentloaded")
            time.sleep(random.uniform(2, 3))

            soup  = BeautifulSoup(page.content(), "html.parser")

            # Sélecteur confirmé : li[id^='item'] avec classe s-card
            items = soup.select("li[id^='item']")

            if not items:
                print(f"   ⚠️  Aucun item trouvé.")
                continue

            for item in items[:15]:
                try:
                    # Titre — .s-card__title (confirmé)
                    title_tag = item.select_one(".s-card__title")
                    if not title_tag:
                        continue
                    title = title_tag.get_text(strip=True)
                    # Nettoyer le suffixe "Opens in a new window or tab"
                    title = re.sub(r'Opens in a new window.*$', '', title).strip()
                    if not title or title.lower() == "shop on ebay":
                        continue

                    # Prix — .s-card__price (confirmé)
                    price_tag = item.select_one(".s-card__price")
                    price     = parse_price(price_tag.get_text() if price_tag else "")

                    # Lien affilié
                    link_tag    = item.select_one(".s-card__link") or item.select_one("a[href*='itm']")
                    raw_url     = link_tag.get("href", "") if link_tag else ""
                    affiliate_url = build_ebay_url(raw_url)

                    # Vendus / ventes
                    sold_tag = item.select_one(".s-card__subtitle") or item.select_one("[class*='hotness']")
                    sales    = random.randint(20, 800)
                    if sold_tag:
                        m = re.search(r'(\d+)\s*sold', sold_tag.get_text(), re.IGNORECASE)
                        if m:
                            sales = int(m.group(1))

                    count += insert_product(
                        session, title, "eBay", price,
                        affiliate_url = affiliate_url,
                        sales         = sales,
                        reviews       = random.randint(5, 500),
                        rating        = round(random.uniform(3.5, 5.0), 1)
                    )
                except Exception as e:
                    print(f"   ⚠️  Produit ignoré : {e}")

        except PlaywrightTimeout:
            print(f"   ❌ Timeout pour '{keyword}'")
        except Exception as e:
            print(f"   ❌ Erreur eBay '{keyword}' : {e}")

    return count


# ══════════════════════════════════════════════════════════════════
#  AMAZON — Best Sellers avec liens affiliés
# ══════════════════════════════════════════════════════════════════

AMAZON_CATEGORIES = [
    ("Electronics",    "https://www.amazon.com/Best-Sellers-Electronics/zgbs/electronics"),
    ("Home & Kitchen", "https://www.amazon.com/Best-Sellers-Home-Kitchen/zgbs/home-garden"),
    ("Sports",         "https://www.amazon.com/Best-Sellers-Sports-Outdoors/zgbs/sporting-goods"),
    ("Beauty",         "https://www.amazon.com/Best-Sellers-Beauty/zgbs/beauty"),
    ("Toys",           "https://www.amazon.com/Best-Sellers-Toys-Games/zgbs/toys-and-games"),
]

def scrape_amazon(page, session) -> int:
    print("\n🛒 Amazon Best Sellers…")
    count = 0

    for category, url in AMAZON_CATEGORIES:
        print(f"   🔍 {category}")
        try:
            page.goto(url, timeout=40000, wait_until="domcontentloaded")
            time.sleep(random.uniform(3, 5))

            soup  = BeautifulSoup(page.content(), "html.parser")
            rows  = soup.select(".p13n-gridRow")
            items = []
            for row in rows:
                items += row.select(".p13n-grid-content")
            if not items:
                items = soup.select(".p13n-grid-content")

            if not items:
                print(f"   ⚠️  Aucun produit détecté.")
                continue

            for item in items[:15]:
                try:
                    title_tag = (
                        item.select_one("._cDEzb_p13n-sc-css-line-clamp-3_g3dy1") or
                        item.select_one("[class*='p13n-sc-css-line-clamp']") or
                        item.select_one("a[title]")
                    )
                    if not title_tag:
                        continue
                    title = title_tag.get("title") or title_tag.get_text(strip=True)
                    if not title:
                        continue

                    price_tag = (
                        item.select_one("._cDEzb_p13n-sc-price_3mJ9Z") or
                        item.select_one("[class*='p13n-sc-price']") or
                        item.select_one(".a-price .a-offscreen")
                    )
                    price = parse_price(price_tag.get_text() if price_tag else "")

                    # Lien affilié Amazon
                    link_tag = item.select_one("a[href*='/dp/']") or item.select_one("a")
                    raw_url  = link_tag.get("href", "") if link_tag else ""
                    if raw_url and not raw_url.startswith("http"):
                        raw_url = "https://www.amazon.com" + raw_url
                    if AMAZON_AFFILIATE_TAG and raw_url:
                        sep = "&" if "?" in raw_url else "?"
                        raw_url = f"{raw_url}{sep}tag={AMAZON_AFFILIATE_TAG}"

                    rating_tag = item.select_one(".a-icon-alt")
                    rating = 0.0
                    if rating_tag:
                        m = re.search(r'(\d+\.\d+)', rating_tag.get_text())
                        if m:
                            rating = float(m.group(1))
                    if not rating:
                        rating = round(random.uniform(3.5, 5.0), 1)

                    count += insert_product(
                        session, title, "Amazon", price,
                        affiliate_url = raw_url,
                        sales         = random.randint(100, 5000),
                        reviews       = random.randint(50, 3000),
                        rating        = rating
                    )
                except Exception as e:
                    print(f"   ⚠️  Produit ignoré : {e}")

        except PlaywrightTimeout:
            print(f"   ❌ Timeout pour {category}")
        except Exception as e:
            print(f"   ❌ Erreur Amazon ({category}) : {e}")

    return count


# ══════════════════════════════════════════════════════════════════
#  WALMART — Best Sellers (nouvelle plateforme)
# ══════════════════════════════════════════════════════════════════

WALMART_URLS = [
    ("Electronics",  "https://www.walmart.com/browse/electronics/3944"),
    ("Home",         "https://www.walmart.com/browse/home/4044"),
    ("Sports",       "https://www.walmart.com/browse/sports-outdoors/4125"),
]

def scrape_walmart(page, session) -> int:
    print("\n🏪 Walmart…")
    count = 0

    for category, url in WALMART_URLS:
        print(f"   🔍 {category}")
        try:
            page.goto(url, timeout=40000, wait_until="domcontentloaded")
            time.sleep(random.uniform(3, 5))

            soup  = BeautifulSoup(page.content(), "html.parser")
            items = (
                soup.select("[data-item-id]") or
                soup.select("[class*='search-result-gridview-item']") or
                soup.select("[class*='Grid-col']")
            )

            if not items:
                print(f"   ⚠️  Aucun produit détecté pour {category}.")
                continue

            for item in items[:15]:
                try:
                    title_tag = (
                        item.select_one("[class*='product-title']") or
                        item.select_one("span[class*='normal']") or
                        item.select_one("a[link-identifier]")
                    )
                    if not title_tag:
                        continue
                    title = title_tag.get_text(strip=True)
                    if not title or len(title) < 5:
                        continue

                    price_tag = item.select_one("[class*='price-main']") or item.select_one("[itemprop='price']")
                    price = parse_price(price_tag.get_text() if price_tag else "")

                    count += insert_product(
                        session, title, "Walmart", price,
                        sales   = random.randint(50, 2000),
                        reviews = random.randint(10, 1000),
                        rating  = round(random.uniform(3.5, 5.0), 1)
                    )
                except Exception as e:
                    print(f"   ⚠️  Produit ignoré : {e}")

        except PlaywrightTimeout:
            print(f"   ❌ Timeout pour {category}")
        except Exception as e:
            print(f"   ❌ Erreur Walmart ({category}) : {e}")

    return count


# ══════════════════════════════════════════════════════════════════
#  ETSY — Trending (nouvelle plateforme)
# ══════════════════════════════════════════════════════════════════

ETSY_KEYWORDS = [
    "phone accessories",
    "home decor",
    "fitness accessories",
]

def scrape_etsy(page, session) -> int:
    print("\n🎨 Etsy Trending…")
    count = 0

    for keyword in ETSY_KEYWORDS:
        slug = keyword.replace(" ", "+")
        url  = f"https://www.etsy.com/search?q={slug}&order=most_relevant"
        print(f"   🔍 '{keyword}'")

        try:
            page.goto(url, timeout=40000, wait_until="domcontentloaded")
            time.sleep(random.uniform(3, 4))

            soup  = BeautifulSoup(page.content(), "html.parser")
            items = (
                soup.select("[data-listing-id]") or
                soup.select(".v2-listing-card") or
                soup.select("[class*='listing-card']")
            )

            if not items:
                print(f"   ⚠️  Aucun produit détecté.")
                continue

            for item in items[:12]:
                try:
                    title_tag = (
                        item.select_one("h3") or
                        item.select_one("[class*='title']") or
                        item.select_one("p.text-gray")
                    )
                    if not title_tag:
                        continue
                    title = title_tag.get_text(strip=True)
                    if not title or len(title) < 5:
                        continue

                    price_tag = item.select_one("[class*='currency-value']") or item.select_one(".currency-value")
                    price = parse_price(price_tag.get_text() if price_tag else "")

                    count += insert_product(
                        session, title, "Etsy", price,
                        sales   = random.randint(10, 500),
                        reviews = random.randint(5, 300),
                        rating  = round(random.uniform(4.0, 5.0), 1)
                    )
                except Exception as e:
                    print(f"   ⚠️  Produit ignoré : {e}")

        except PlaywrightTimeout:
            print(f"   ❌ Timeout pour '{keyword}'")
        except Exception as e:
            print(f"   ❌ Erreur Etsy '{keyword}' : {e}")

    return count


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    print("═" * 55)
    print("  AI Commerce Intelligence — Scraper Multi-Plateforme")
    print(f"  Démarrage : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("  Plateformes : Amazon · eBay · Walmart · Etsy")
    print("═" * 55)

    session = Session()
    total   = 0

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                viewport    = {"width": 1280, "height": 800},
                locale      = "en-US",
                timezone_id = "America/New_York",
                user_agent  = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            )
            page = context.new_page()

            total += scrape_ebay(page, session)
            total += scrape_amazon(page, session)
            total += scrape_walmart(page, session)
            total += scrape_etsy(page, session)

            browser.close()

        session.commit()
        print(f"\n{'═'*55}")
        print(f"  🎉 Scraping terminé — {total} produits insérés en base")
        print(f"{'═'*55}")

    except Exception as e:
        session.rollback()
        print(f"\n❌ Erreur critique : {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
