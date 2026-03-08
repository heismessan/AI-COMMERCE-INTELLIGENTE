"""
trends_scraper.py — AI Commerce Intelligence
─────────────────────────────────────────────────────────
Récupère les tendances Google Trends via le flux RSS officiel.
Pas de librairie tierce — utilise uniquement requests + xml.

Prérequis : pip install requests (déjà installé)
"""

import requests
import datetime
import time
import logging
import json
import xml.etree.ElementTree as ET
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker

# ══════════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════════

MYSQL_USER     = "root"
MYSQL_PASSWORD = "Attraction24"
MYSQL_HOST     = "127.0.0.1"
MYSQL_DB       = "ai_commerce"

# Zones géographiques — codes Google Trends RSS
GEO_ZONES = [
    {"code": "FR", "label": "France"},
    {"code": "US", "label": "États-Unis"},
    {"code": "NG", "label": "Nigeria"},
    {"code": "GH", "label": "Ghana"},
    {"code": "ZA", "label": "Afrique du Sud"},
]
# Note : TG/SN/CI non supportés par le RSS Google Trends — on prend les voisins africains

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s  %(levelname)s  %(message)s",
    datefmt = "%H:%M:%S",
)
log = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
#  MODÈLE BASE DE DONNÉES
# ══════════════════════════════════════════════════════════════════

Base = declarative_base()

class Trend(Base):
    __tablename__ = "trends"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    keyword     = Column(String(255), nullable=False)
    geo_code    = Column(String(10),  default="")
    geo_label   = Column(String(50),  default="Mondial")
    trend_value = Column(Float,       default=0.0)   # rang inversé (1er = 100)
    related     = Column(Text,        default="")    # JSON liste mots associés
    category    = Column(String(100), default="")
    scraped_at  = Column(DateTime,    default=datetime.datetime.utcnow)

engine  = create_engine(
    f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}",
    echo=False
)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)


# ══════════════════════════════════════════════════════════════════
#  SCRAPER RSS GOOGLE TRENDS
# ══════════════════════════════════════════════════════════════════

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9",
}

def fetch_daily_trends(geo_code: str, geo_label: str) -> list:
    """
    Récupère le top 20 des tendances du jour via le flux RSS Google Trends.
    URL : https://trends.google.com/trends/trendingsearches/daily/rss?geo=XX
    """
    url = f"https://trends.google.com/trends/trendingsearches/daily/rss?geo={geo_code}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            log.warning(f"  ⚠️  {geo_label} : HTTP {r.status_code}")
            return []

        root = ET.fromstring(r.content)
        items = root.findall(".//item")

        results = []
        for i, item in enumerate(items[:20]):
            title = item.findtext("title") or ""
            if not title:
                continue

            # Trafic approximatif (ex: "200K+")
            traffic_el = item.find("{https://trends.google.com/trends/trendingsearches/daily}approx_traffic")
            traffic_str = traffic_el.text if traffic_el is not None else ""

            # Score basé sur le rang (1er = 100, 2ème = 95, etc.)
            score = max(10, 100 - (i * 5))

            # Mots-clés associés dans les news liées
            related_titles = []
            for news in item.findall(".//ht:news_item", {"ht": "https://trends.google.com/trends/trendingsearches/daily"}):
                news_title = news.findtext("{https://trends.google.com/trends/trendingsearches/daily}news_item_title")
                if news_title:
                    related_titles.append(news_title[:60])

            results.append({
                "keyword":     title,
                "trend_value": float(score),
                "related":     json.dumps(related_titles[:3]),
                "geo_code":    geo_code,
                "geo_label":   geo_label,
                "category":    detect_category(title),
            })

        log.info(f"  ✅ {geo_label} : {len(results)} tendances")
        return results

    except requests.exceptions.ConnectionError:
        log.warning(f"  ⚠️  {geo_label} : connexion impossible")
        return []
    except ET.ParseError as e:
        log.warning(f"  ⚠️  {geo_label} : erreur XML — {e}")
        return []
    except Exception as e:
        log.warning(f"  ⚠️  {geo_label} : {e}")
        return []


def fetch_realtime_trends(geo_code: str, geo_label: str) -> list:
    """
    Récupère les tendances en temps réel via le flux RSS.
    URL : https://trends.google.com/trends/trendingsearches/realtime?geo=XX&hl=fr&category=all&fi=0&fs=0&ri=300&rs=20&sort=0
    """
    url = (
        f"https://trends.google.com/trends/trendingsearches/realtime"
        f"?geo={geo_code}&hl=fr&category=all&fi=0&fs=0&ri=300&rs=20&sort=0"
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return []

        # Réponse JSON
        data = r.json()
        items = data.get("storySummaries", {}).get("trendingStories", [])

        results = []
        for i, story in enumerate(items[:15]):
            title = story.get("title") or story.get("entityNames", [""])[0]
            if not title:
                continue

            related = [a.get("articleTitle", "")[:60] for a in story.get("articles", [])[:3]]

            results.append({
                "keyword":     title,
                "trend_value": float(max(10, 100 - (i * 6))),
                "related":     json.dumps([r for r in related if r]),
                "geo_code":    geo_code,
                "geo_label":   geo_label + " (RT)",
                "category":    detect_category(title),
            })

        log.info(f"  ✅ {geo_label} realtime : {len(results)} tendances")
        return results

    except Exception:
        return []


def detect_category(keyword: str) -> str:
    kw = keyword.lower()
    if any(w in kw for w in ["robe", "sneaker", "parfum", "perruque", "sac", "bijou", "montre", "mode", "vêtement", "fashion", "beauty", "cosmetic"]):
        return "Mode & Beauté"
    if any(w in kw for w in ["smartphone", "iphone", "samsung", "écouteur", "chargeur", "tablette", "watch", "solaire", "power", "tech", "laptop", "phone"]):
        return "Électronique"
    if any(w in kw for w in ["ventilateur", "climatiseur", "friteuse", "robot", "matelas", "rideau", "maison", "home", "kitchen"]):
        return "Maison"
    if any(w in kw for w in ["sport", "haltère", "vélo", "tapis", "santé", "health", "fitness", "workout"]):
        return "Sport & Santé"
    if any(w in kw for w in ["bébé", "couche", "jouet", "enfant", "poussette", "baby", "kid"]):
        return "Bébé & Enfant"
    return "Général"


# ══════════════════════════════════════════════════════════════════
#  SAUVEGARDE
# ══════════════════════════════════════════════════════════════════

def save_trends(trends_list: list) -> int:
    if not trends_list:
        return 0
    session = Session()
    try:
        for t in trends_list:
            session.add(Trend(
                keyword     = t.get("keyword", "")[:255],
                geo_code    = t.get("geo_code", ""),
                geo_label   = t.get("geo_label", "")[:50],
                trend_value = t.get("trend_value", 0.0),
                related     = t.get("related", ""),
                category    = t.get("category", ""),
                scraped_at  = datetime.datetime.utcnow(),
            ))
        session.commit()
        return len(trends_list)
    except Exception as e:
        session.rollback()
        log.error(f"❌ Sauvegarde échouée : {e}")
        return 0
    finally:
        session.close()


# ══════════════════════════════════════════════════════════════════
#  JOB PRINCIPAL
# ══════════════════════════════════════════════════════════════════

def run_trends_scraper() -> int:
    log.info("═" * 50)
    log.info("  🔍 Google Trends Scraper")
    log.info(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log.info("═" * 50)

    # Vider les anciennes tendances
    session = Session()
    try:
        from sqlalchemy import text
        old = session.query(Trend).count()
        session.execute(text("DELETE FROM trends"))
        session.commit()
        log.info(f"🗑️  {old} anciennes tendances supprimées")
    except Exception as e:
        session.rollback()
        log.error(f"❌ Vidage échoué : {e}")
    finally:
        session.close()

    total = 0
    for zone in GEO_ZONES:
        log.info(f"\n📍 {zone['label']} ({zone['code']})")

        # Tendances du jour
        daily = fetch_daily_trends(zone["code"], zone["label"])
        total += save_trends(daily)
        time.sleep(2)

        # Tendances temps réel
        rt = fetch_realtime_trends(zone["code"], zone["label"])
        total += save_trends(rt)
        time.sleep(3)

    log.info(f"\n🎉 Terminé — {total} tendances en base")
    log.info("═" * 50)
    return total


# ══════════════════════════════════════════════════════════════════
#  LECTURE (pour l'API Flask)
# ══════════════════════════════════════════════════════════════════

def get_top_trends(geo_code="", limit=50, category="") -> list:
    session = Session()
    try:
        from sqlalchemy import desc
        q = session.query(Trend)
        if geo_code and geo_code != "all":
            q = q.filter(Trend.geo_code == geo_code)
        if category:
            q = q.filter(Trend.category == category)
        trends = q.order_by(desc(Trend.trend_value)).limit(limit).all()
        return [{
            "id":          t.id,
            "keyword":     t.keyword,
            "geo_code":    t.geo_code,
            "geo_label":   t.geo_label,
            "trend_value": t.trend_value,
            "category":    t.category,
            "related":     json.loads(t.related) if t.related else [],
            "scraped_at":  t.scraped_at.isoformat() if t.scraped_at else None,
        } for t in trends]
    finally:
        session.close()


def get_trends_stats() -> dict:
    session = Session()
    try:
        from sqlalchemy import func, desc
        total = session.query(Trend).count()
        top   = session.query(Trend).order_by(desc(Trend.trend_value)).first()
        zones = session.query(Trend.geo_label, func.count(Trend.id)).group_by(Trend.geo_label).all()
        cats  = session.query(Trend.category,  func.count(Trend.id)).group_by(Trend.category).all()
        last  = session.query(func.max(Trend.scraped_at)).scalar()
        return {
            "total":       total,
            "top_keyword": top.keyword if top else "—",
            "top_score":   top.trend_value if top else 0,
            "by_zone":     {z: c for z, c in zones},
            "by_category": {cat: c for cat, c in cats},
            "last_update": last.isoformat() if last else None,
        }
    finally:
        session.close()


# ══════════════════════════════════════════════════════════════════
#  TEST
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Test Google Trends RSS — France…")
    results = fetch_daily_trends("FR", "France")
    if results:
        print(f"\n✅ {len(results)} tendances récupérées !")
        for r in results[:5]:
            print(f"  #{int((100 - r['trend_value']) / 5) + 1}  {r['keyword']:35} → {r['trend_value']:.0f}/100  [{r['category']}]")
        print("\nLancement du scraping complet…")
        total = run_trends_scraper()
        print(f"\n✅ {total} tendances sauvegardées en base !")
    else:
        print("❌ Aucune donnée — vérifie ta connexion internet.")
