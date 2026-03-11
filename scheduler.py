"""
scheduler.py
Scheduler central pour AI Commerce Intelligence
"""

import schedule
import time
import logging
from datetime import datetime
from sqlalchemy import text

from database import SessionLocal, engine, Product
from scraper_multi import main as run_scraper
from scoring_ai import recalculate_all_scores
from trends_scraper import run_trends_scraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
)

log = logging.getLogger(__name__)


# ─────────────────────────────────────────
# JOB PRINCIPAL
# ─────────────────────────────────────────

def scrape_job():

    log.info("══════════════════════════════════════")
    log.info("🔄 Scraping automatique démarré")
    log.info(datetime.now())
    log.info("══════════════════════════════════════")

    # vider table
    try:
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM products")).scalar()
            conn.execute(text("DELETE FROM products"))
            conn.commit()

        log.info(f"{count} anciens produits supprimés")

    except Exception as e:
        log.error(f"Erreur delete : {e}")
        return

    # scraping
    try:
        log.info("Scraping en cours ...")
        run_scraper()
        log.info("Scraping terminé")

    except Exception as e:
        log.error(f"Erreur scraping : {e}")
        return

    # scoring
    try:
        recalculate_all_scores()
        log.info("Scores recalculés")

    except Exception as e:
        log.error(f"Erreur scoring : {e}")

    # trends
    try:
        run_trends_scraper()
        log.info("Trends mises à jour")

    except Exception as e:
        log.error(f"Erreur trends : {e}")

    # résumé
    session = SessionLocal()

    try:
        total = session.query(Product).count()
        log.info(f"{total} produits en base")

    finally:
        session.close()

    log.info("Scraping terminé")


# ─────────────────────────────────────────
# START SCHEDULER
# ─────────────────────────────────────────

def start_scheduler():

    log.info("Scheduler démarré")
    log.info("Scraping prévu à 00:00 et 12:00")

    schedule.every().day.at("00:00").do(scrape_job)
    schedule.every().day.at("12:00").do(scrape_job)

    # premier scraping
    log.info("Premier scraping lancé au démarrage")
    scrape_job()

    while True:

        schedule.run_pending()
        time.sleep(30)