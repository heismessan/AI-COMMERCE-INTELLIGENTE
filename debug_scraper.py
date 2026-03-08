"""
debug_scraper.py — Diagnostic HTML
─────────────────────────────────────────────────────────
Ce script ouvre eBay et Amazon, sauvegarde le HTML reçu
dans des fichiers .html pour qu'on voie exactement
quels sélecteurs utiliser.

Usage :
    python debug_scraper.py
"""

import time
import random
from playwright.sync_api import sync_playwright

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

        # ── eBay ──────────────────────────────────────────────────
        print("Ouverture eBay…")
        page.goto("https://www.ebay.com/sch/i.html?_nkw=wireless+earbuds&_sop=12",
                  timeout=40000, wait_until="domcontentloaded")
        time.sleep(4)

        html_ebay = page.content()
        with open("debug_ebay.html", "w", encoding="utf-8") as f:
            f.write(html_ebay)
        print(f"✅ debug_ebay.html sauvegardé ({len(html_ebay)} caractères)")

        # Afficher les 20 premières classes trouvées pour chercher les bons sélecteurs
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_ebay, "html.parser")
        classes_found = set()
        for tag in soup.find_all(True):
            for c in tag.get("class", []):
                if "item" in c.lower() or "product" in c.lower() or "result" in c.lower():
                    classes_found.add(c)
        print("Classes eBay contenant 'item/product/result' :")
        for c in sorted(classes_found)[:30]:
            print(f"   .{c}")

        time.sleep(2)

        # ── Amazon ────────────────────────────────────────────────
        print("\nOuverture Amazon Best Sellers Electronics…")
        page.goto("https://www.amazon.com/Best-Sellers-Electronics/zgbs/electronics",
                  timeout=40000, wait_until="domcontentloaded")
        time.sleep(4)

        html_amazon = page.content()
        with open("debug_amazon.html", "w", encoding="utf-8") as f:
            f.write(html_amazon)
        print(f"✅ debug_amazon.html sauvegardé ({len(html_amazon)} caractères)")

        soup2 = BeautifulSoup(html_amazon, "html.parser")
        classes_found2 = set()
        for tag in soup2.find_all(True):
            for c in tag.get("class", []):
                if any(k in c.lower() for k in ["item", "product", "zg", "p13n", "result"]):
                    classes_found2.add(c)
        print("Classes Amazon contenant 'item/product/zg/p13n' :")
        for c in sorted(classes_found2)[:30]:
            print(f"   .{c}")

        browser.close()
        print("\nDiagnostic terminé. Envoie-moi le contenu affiché ici !")

if __name__ == "__main__":
    debug()
