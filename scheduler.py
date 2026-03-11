"""
scheduler.py
Scheduler automatique du scraping
"""

import schedule
import time
import logging
from datetime import datetime

from scraper_multi import main as run_scraper
from scoring_ai import recalculate_all_scores
from trends_scraper import run_trends_scraper


logging.basicConfig(level=logging.INFO)

log = logging.getLogger(__name__)


def scrape_job():

    log.info("Scraping job started")
    log.info(datetime.now())

    try:
        run_scraper()
    except Exception as e:
        log.error(f"Scraper error {e}")

    try:
        recalculate_all_scores()
    except Exception as e:
        log.error(f"Scoring error {e}")

    try:
        run_trends_scraper()
    except Exception as e:
        log.error(f"Trends error {e}")


def start_scheduler():

    log.info("Scheduler started")

    schedule.every().day.at("00:00").do(scrape_job)
    schedule.every().day.at("12:00").do(scrape_job)

    scrape_job()

    while True:

        schedule.run_pending()

        time.sleep(30)