"""
debug_walmart_etsy.py — Diagnostic HTML
─────────────────────────────────────────────────────────
Sauvegarde le HTML de Walmart et Etsy pour trouver
les vrais sélecteurs CSS.

Usage :
    python debug_walmart_etsy.py
"""

import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

def debug():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport    = {"width": 1280, "height": 800},
            locale      = "en-US",
            timezone_id = "America/New_York",
            user_agent  = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        )
        page = context.new_page()

        # ── WALMART ───────────────────────────────────────────────
        print("Ouverture Walmart Electronics…")
        page.goto("https://www.walmart.com/browse/electronics/3944",
                  timeout=40000, wait_until="domcontentloaded")
        time.sleep(5)  # attendre le JS

        html_walmart = page.content()
        with open("debug_walmart.html", "w", encoding="utf-8") as f:
            f.write(html_walmart)
        print(f"✅ debug_walmart.html sauvegardé ({len(html_walmart)} caractères)")

        soup = BeautifulSoup(html_walmart, "html.parser")
        classes_found = set()
        for tag in soup.find_all(True):
            for c in tag.get("class", []):
                if any(k in c.lower() for k in ["item", "product", "tile", "card", "result", "grid"]):
                    classes_found.add(c)
        print("Classes Walmart pertinentes :")
        for c in sorted(classes_found)[:30]:
            print(f"   .{c}")

        # Chercher aussi les data-attributes
        data_attrs = set()
        for tag in soup.find_all(True):
            for attr in tag.attrs:
                if attr.startswith("data-") and any(k in attr for k in ["item", "product", "id"]):
                    data_attrs.add(attr)
        print("Data-attributes Walmart :")
        for a in sorted(data_attrs)[:15]:
            print(f"   [{a}]")

        time.sleep(2)

        # ── ETSY ──────────────────────────────────────────────────
        print("\nOuverture Etsy phone accessories…")
        page.goto("https://www.etsy.com/search?q=phone+accessories&order=most_relevant",
                  timeout=40000, wait_until="domcontentloaded")
        time.sleep(5)

        html_etsy = page.content()
        with open("debug_etsy.html", "w", encoding="utf-8") as f:
            f.write(html_etsy)
        print(f"✅ debug_etsy.html sauvegardé ({len(html_etsy)} caractères)")

        soup2 = BeautifulSoup(html_etsy, "html.parser")
        classes_found2 = set()
        for tag in soup2.find_all(True):
            for c in tag.get("class", []):
                if any(k in c.lower() for k in ["item", "product", "listing", "card", "result", "tile"]):
                    classes_found2.add(c)
        print("Classes Etsy pertinentes :")
        for c in sorted(classes_found2)[:30]:
            print(f"   .{c}")

        data_attrs2 = set()
        for tag in soup2.find_all(True):
            for attr in tag.attrs:
                if attr.startswith("data-") and any(k in attr for k in ["listing", "item", "product"]):
                    data_attrs2.add(attr)
        print("Data-attributes Etsy :")
        for a in sorted(data_attrs2)[:15]:
            print(f"   [{a}]")

        browser.close()
        print("\n✅ Diagnostic terminé — envoie-moi ce qui s'affiche ici !")

if __name__ == "__main__":
    debug()
