"""
scheduler.py — AI Commerce Intelligence
─────────────────────────────────────────────────────────
Lance le scraper automatiquement deux fois par jour :
  • Minuit  (00:00)
  • Midi    (12:00)

À chaque exécution :
  1. Vide complètement la table products
  2. Relance le scraper Amazon + eBay
  3. Recalcule tous les scores

Prérequis :
    pip install schedule

Usage :
    python scheduler.py
    → Tourne en arrière-plan, ne pas fermer la console
"""

import schedule
import time
import logging
from datetime import datetime
from sqlalchemy import text
from database import Session, engine, Product
from scraper_multi import main as run_scraper
from scoring_ai import recalculate_all_scores
from trends_scraper import run_trends_scraper

# ── Logging ────────────────────────────────────────────────────────
logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s  %(levelname)s  %(message)s",
    datefmt = "%Y-%m-%d %H:%M:%S",
    handlers = [
        logging.StreamHandler(),
        logging.FileHandler("scheduler.log", encoding="utf-8"),
    ]
)
log = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
#  JOB PRINCIPAL
# ══════════════════════════════════════════════════════════════════

def scrape_job():
    log.info("═" * 50)
    log.info(f"  🔄 Démarrage du scraping automatique")
    log.info(f"  Heure : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("═" * 50)

    session = Session()
    try:
        # ── Étape 1 : Vider la base ────────────────────────────────
        count_before = session.query(Product).count()
        session.execute(text("DELETE FROM products"))
        session.commit()
        log.info(f"🗑️  Table vidée ({count_before} anciens produits supprimés)")

    except Exception as e:
        session.rollback()
        log.error(f"❌ Erreur lors du vidage : {e}")
        return
    finally:
        session.close()

    # ── Étape 2 : Scraper ──────────────────────────────────────────
    try:
        log.info("🚀 Lancement du scraper…")
        run_scraper()
        log.info("✅ Scraping terminé")
    except Exception as e:
        log.error(f"❌ Erreur scraper : {e}")
        return

    # ── Étape 3 : Recalculer les scores ───────────────────────────
    try:
        log.info("📊 Recalcul des scores…")
        recalculate_all_scores()
        log.info("✅ Scores recalculés")
    except Exception as e:
        log.error(f"❌ Erreur scoring : {e}")

    # ── Résumé ─────────────────────────────────────────────────────
    session2 = Session()
    try:
        total = session2.query(Product).count()
        log.info(f"🎉 Mise à jour terminée — {total} produits en base")
    finally:
        session2.close()

    log.info("═" * 50)


# ══════════════════════════════════════════════════════════════════
#  PLANIFICATION
# ══════════════════════════════════════════════════════════════════

def main():
    print("═" * 50)
    print("  AI Commerce Intelligence — Scheduler")
    print("  Scraping automatique : 00:00 et 12:00")
    print("  Fichier log : scheduler.log")
    print("═" * 50)

    # Planifier les deux exécutions quotidiennes
    schedule.every().day.at("00:00").do(scrape_job)
    schedule.every().day.at("12:00").do(scrape_job)

    log.info("✅ Scheduler démarré")
    log.info(f"   Prochain scraping : {schedule.next_run()}")

    # Afficher les prochaines exécutions
    print(f"\n  Prochain scraping prévu : {schedule.next_run()}")
    print("  (garde cette console ouverte)\n")

    # Option : lancer immédiatement au démarrage
    print("  ⚡ Lancement immédiat du premier scraping…")
    scrape_job()

    # Boucle principale
    while True:
        schedule.run_pending()
        time.sleep(30)   # vérifie toutes les 30 secondes


if __name__ == "__main__":
    main()
