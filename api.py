"""
api.py — AI Commerce Intelligence
API principale : Auth + Produits + Trends + Scheduler intégré
"""

import os
import datetime
import threading
import time
import logging
from functools import wraps

from flask import Flask, jsonify, request, g, redirect
from flask_cors import CORS
from flask_bcrypt import Bcrypt

from sqlalchemy import (
    create_engine, Column, Integer, String,
    Boolean, DateTime, func, desc, text
)
from sqlalchemy.orm import declarative_base, sessionmaker

import jwt as pyjwt
import schedule

from config import get_db_url, JWT_SECRET, APP_URL
from database import Product, SessionLocal
from email_service import (
    send_confirmation_email, send_welcome_email,
    generate_verification_token, token_expiry
)
from trends_scraper import get_top_trends, get_trends_stats

# ─────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────
# APP
# ─────────────────────────────────────────

app    = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)
bcrypt = Bcrypt(app)

# ─────────────────────────────────────────
# USERS DATABASE
# ─────────────────────────────────────────

Base         = declarative_base()
engine_users = create_engine(get_db_url(), pool_pre_ping=True, pool_recycle=280)
SessionUsers = sessionmaker(autocommit=False, autoflush=False, bind=engine_users)


class User(Base):
    __tablename__ = "users"

    id             = Column(Integer,     primary_key=True, autoincrement=True)
    email          = Column(String(255), unique=True, nullable=False)
    password_hash  = Column(String(255), nullable=False)
    plan           = Column(String(20),  default="free")
    created_at     = Column(DateTime,    default=datetime.datetime.utcnow)
    is_active      = Column(Boolean,     default=True)
    is_verified    = Column(Boolean,     default=False)
    verify_token   = Column(String(100), default="")
    verify_expiry  = Column(DateTime,    nullable=True)


Base.metadata.create_all(engine_users, checkfirst=True)

# ─────────────────────────────────────────
# AUTH HELPERS
# ─────────────────────────────────────────

def generate_token(user_id, plan):
    payload = {
        "user_id": user_id,
        "plan":    plan,
        "exp":     datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verify_token(token):
    try:
        return pyjwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError:
        return None
    except pyjwt.InvalidTokenError:
        return None


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Token manquant"}), 401
        payload = verify_token(auth.split(" ")[1])
        if not payload:
            return jsonify({"error": "Token invalide"}), 401
        g.user_id = payload["user_id"]
        g.plan    = payload["plan"]
        return f(*args, **kwargs)
    return decorated


def require_pro(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Token manquant"}), 401
        payload = verify_token(auth.split(" ")[1])
        if not payload:
            return jsonify({"error": "Token invalide"}), 401
        if payload["plan"] != "pro":
            return jsonify({"error": "Plan Pro requis"}), 403
        g.user_id = payload["user_id"]
        g.plan    = payload["plan"]
        return f(*args, **kwargs)
    return decorated

# ─────────────────────────────────────────
# PAGES STATIQUES
# ─────────────────────────────────────────

@app.route("/")
def home():
    return app.send_static_file("login.html")

@app.route("/login")
def login_page():
    return app.send_static_file("login.html")

@app.route("/dashboard")
def dashboard_page():
    return app.send_static_file("dashboard.html")

@app.route("/health")
def health_check():
    return jsonify({"status": "ok"})

# ─────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────

@app.route("/auth/register", methods=["POST"])
def register():
    data     = request.get_json() or {}
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email et mot de passe requis"}), 400

    session = SessionUsers()
    try:
        if session.query(User).filter(User.email == email).first():
            return jsonify({"error": "Email déjà utilisé"}), 409

        user = User(
            email         = email,
            password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        try:
            token              = generate_verification_token()
            user.verify_token  = token
            user.verify_expiry = token_expiry()
            session.commit()
            send_confirmation_email(email, token)
        except Exception as e:
            log.warning(f"⚠️ Email non envoyé : {e}")

        return jsonify({"success": True, "message": "Vérifie ta boîte mail pour confirmer ton compte."})
    finally:
        session.close()


@app.route("/auth/confirm-email", methods=["GET"])
def confirm_email():
    token = request.args.get("token", "")
    if not token:
        return jsonify({"error": "Token manquant"}), 400

    session = SessionUsers()
    try:
        user = session.query(User).filter(User.verify_token == token).first()
        if not user:
            return jsonify({"error": "Token invalide"}), 400
        if user.verify_expiry and datetime.datetime.utcnow() > user.verify_expiry:
            return jsonify({"error": "Token expiré"}), 400

        user.is_verified  = True
        user.verify_token = ""
        session.commit()

        try:
            send_welcome_email(user.email)
        except Exception:
            pass

        jwt_token = generate_token(user.id, user.plan)
        return redirect(f"/?confirmed=1&token={jwt_token}&email={user.email}")
    finally:
        session.close()


@app.route("/auth/login", methods=["POST"])
def login():
    data     = request.get_json() or {}
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")

    session = SessionUsers()
    try:
        user = session.query(User).filter(User.email == email).first()
        if not user:
            return jsonify({"error": "Email incorrect"}), 401
        if not bcrypt.check_password_hash(user.password_hash, password):
            return jsonify({"error": "Mot de passe incorrect"}), 401

        token = generate_token(user.id, user.plan)
        return jsonify({
            "token": token,
            "user":  {"email": user.email, "plan": user.plan}
        })
    finally:
        session.close()


@app.route("/auth/me", methods=["GET"])
@require_auth
def me():
    session = SessionUsers()
    try:
        user = session.query(User).filter(User.id == g.user_id).first()
        if not user:
            return jsonify({"error": "Utilisateur introuvable"}), 404
        return jsonify({"email": user.email, "plan": user.plan})
    finally:
        session.close()

# ─────────────────────────────────────────
# PRODUCTS
# ─────────────────────────────────────────

def product_to_dict(p):
    return {
        "id":            p.id,
        "title":         p.title,
        "platform":      p.platform,
        "price":         p.price,
        "margin":        round(p.margin * 100, 1),
        "sales":         p.sales,
        "reviews":       p.reviews,
        "rating":        p.rating,
        "score":         p.opportunity_score,
        "affiliate_url": getattr(p, "affiliate_url", ""),
    }


@app.route("/api/products")
def get_products():
    platform = request.args.get("platform", "")
    limit    = min(200, int(request.args.get("limit", 50)))
    offset   = int(request.args.get("offset", 0))
    q = SessionLocal()
    try:
        query = q.query(Product)
        if platform:
            query = query.filter(Product.platform == platform)
        total    = query.count()
        products = query.order_by(desc(Product.opportunity_score)).offset(offset).limit(limit).all()
        return jsonify({"success": True, "total": total, "products": [product_to_dict(p) for p in products]})
    finally:
        q.close()


@app.route("/api/products/top")
def get_top_products():
    limit = min(50, int(request.args.get("limit", 20)))
    q = SessionLocal()
    try:
        products = q.query(Product).order_by(desc(Product.opportunity_score)).limit(limit).all()
        return jsonify({"success": True, "products": [product_to_dict(p) for p in products]})
    finally:
        q.close()


@app.route("/api/products/search")
def search_products():
    query_str = request.args.get("q", "").strip()
    limit     = min(100, int(request.args.get("limit", 50)))
    q = SessionLocal()
    try:
        products = (
            q.query(Product)
            .filter(Product.title.ilike(f"%{query_str}%"))
            .order_by(desc(Product.opportunity_score))
            .limit(limit).all()
        )
        return jsonify({"success": True, "products": [product_to_dict(p) for p in products]})
    finally:
        q.close()


@app.route("/api/products/<int:product_id>")
def get_product(product_id):
    q = SessionLocal()
    try:
        product = q.query(Product).filter(Product.id == product_id).first()
        if not product:
            return jsonify({"success": False, "error": "Produit introuvable"}), 404
        return jsonify({"success": True, "product": product_to_dict(product)})
    finally:
        q.close()


@app.route("/api/stats")
def stats():
    q = SessionLocal()
    try:
        total     = q.query(Product).count()
        avg_score = q.query(func.avg(Product.opportunity_score)).scalar() or 0
        avg_price = q.query(func.avg(Product.price)).scalar() or 0
        platforms = q.query(Product.platform, func.count(Product.id)).group_by(Product.platform).all()
        return jsonify({
            "success":        True,
            "total_products": total,
            "avg_score":      round(float(avg_score), 2),
            "avg_price":      round(float(avg_price), 2),
            "by_platform":    {p: c for p, c in platforms},
        })
    finally:
        q.close()


@app.route("/api/platforms")
def get_platforms():
    q = SessionLocal()
    try:
        platforms = q.query(Product.platform).distinct().all()
        return jsonify({"success": True, "platforms": [p[0] for p in platforms]})
    finally:
        q.close()


@app.route("/products/free")
def products_free():
    q = SessionLocal()
    try:
        products = q.query(Product).order_by(desc(Product.scraped_at)).limit(10).all()
        return jsonify({"plan": "free", "products": [product_to_dict(p) for p in products]})
    finally:
        q.close()


@app.route("/products/pro")
@require_pro
def products_pro():
    q = SessionLocal()
    try:
        products = q.query(Product).order_by(desc(Product.opportunity_score)).limit(100).all()
        return jsonify({"plan": "pro", "products": [product_to_dict(p) for p in products]})
    finally:
        q.close()

# ─────────────────────────────────────────
# TRENDS
# ─────────────────────────────────────────

@app.route("/api/trends")
def trends():
    geo   = request.args.get("geo", "")
    limit = int(request.args.get("limit", 50))
    data  = get_top_trends(geo_code=geo, limit=limit)
    return jsonify({"success": True, "count": len(data), "trends": data})


@app.route("/api/trends/stats")
def trends_stats():
    return jsonify({"success": True, **get_trends_stats()})

# ─────────────────────────────────────────
# SCHEDULER INTÉGRÉ — scraping 2x/jour
# ─────────────────────────────────────────

def scrape_job():
    log.info("═" * 50)
    log.info("🔄 Scraping automatique démarré")
    log.info(f"   {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("═" * 50)

    # Vider la table products
    try:
        from database import engine as db_engine
        with db_engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM products")).scalar()
            conn.execute(text("DELETE FROM products"))
            conn.commit()
        log.info(f"🗑️  {count} anciens produits supprimés")
    except Exception as e:
        log.error(f"❌ Erreur vidage : {e}")
        return

    # Scraper
    try:
        from scraper_multi import main as run_scraper
        log.info("🚀 Scraping en cours…")
        run_scraper()
        log.info("✅ Scraping terminé")
    except Exception as e:
        log.error(f"❌ Erreur scraper : {e}")
        return

    # Scoring
    try:
        from scoring_ai import recalculate_all_scores
        recalculate_all_scores()
        log.info("✅ Scores recalculés")
    except Exception as e:
        log.error(f"❌ Erreur scoring : {e}")

    # Trends
    try:
        from trends_scraper import run_trends_scraper
        run_trends_scraper()
        log.info("✅ Tendances mises à jour")
    except Exception as e:
        log.error(f"❌ Erreur trends : {e}")

    # Résumé
    try:
        q = SessionLocal()
        total = q.query(Product).count()
        q.close()
        log.info(f"🎉 Terminé — {total} produits en base")
    except Exception:
        pass
    log.info("═" * 50)


def start_scheduler():
    log.info("⏰ Scheduler démarré — scraping à 00:00 et 12:00 UTC")
    schedule.every().day.at("00:00").do(scrape_job)
    schedule.every().day.at("12:00").do(scrape_job)

    # Premier scraping 60 secondes après le démarrage
    log.info("⚡ Premier scraping dans 60 secondes…")
    threading.Timer(60, scrape_job).start()

    while True:
        schedule.run_pending()
        time.sleep(30)


# Démarrer le scheduler en arrière-plan
threading.Thread(target=start_scheduler, daemon=True).start()

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
