"""
api.py — AI Commerce Intelligence
API principale : Auth + Produits + Trends
Scheduler externe lancé au démarrage
"""

import os
import datetime
import threading
import logging
from functools import wraps

from flask import Flask, jsonify, request, g, redirect
from flask_cors import CORS
from flask_bcrypt import Bcrypt

from sqlalchemy import (
    create_engine, Column, Integer, String,
    Boolean, DateTime, func, desc
)
from sqlalchemy.orm import declarative_base, sessionmaker

import jwt as pyjwt

from config import get_db_url, JWT_SECRET
from database import Product, SessionLocal
from scheduler import start_scheduler

from email_service import (
    send_confirmation_email,
    send_welcome_email,
    generate_verification_token,
    token_expiry
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

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)
bcrypt = Bcrypt(app)


# ─────────────────────────────────────────
# USERS DATABASE
# ─────────────────────────────────────────

Base = declarative_base()

engine_users = create_engine(
    get_db_url(),
    pool_pre_ping=True,
    pool_recycle=280
)

SessionUsers = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine_users
)


class User(Base):

    __tablename__ = "users"

    id            = Column(Integer, primary_key=True)
    email         = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    plan          = Column(String(20), default="free")

    created_at    = Column(DateTime, default=datetime.datetime.utcnow)

    is_active     = Column(Boolean, default=True)
    is_verified   = Column(Boolean, default=False)

    verify_token  = Column(String(100), default="")
    verify_expiry = Column(DateTime, nullable=True)


Base.metadata.create_all(engine_users, checkfirst=True)


# ─────────────────────────────────────────
# AUTH HELPERS
# ─────────────────────────────────────────

def generate_token(user_id, plan):

    payload = {
        "user_id": user_id,
        "plan": plan,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
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
def health():
    return jsonify({"status": "ok"})


# ─────────────────────────────────────────
# AUTH ROUTES
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
            email=email,
            password_hash=bcrypt.generate_password_hash(password).decode("utf-8")
        )

        session.add(user)
        session.commit()
        session.refresh(user)

        try:
            token = generate_verification_token()
            user.verify_token = token
            user.verify_expiry = token_expiry()
            session.commit()

            send_confirmation_email(email, token)

        except Exception as e:
            log.warning(f"Email non envoyé : {e}")

        return jsonify({"success": True})

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
            "user": {
                "email": user.email,
                "plan": user.plan
            }
        })

    finally:
        session.close()


# ─────────────────────────────────────────
# PRODUCTS API
# ─────────────────────────────────────────

def product_to_dict(p):

    return {
        "id": p.id,
        "title": p.title,
        "platform": p.platform,
        "price": p.price,
        "margin": round(p.margin * 100, 1),
        "sales": p.sales,
        "reviews": p.reviews,
        "rating": p.rating,
        "score": p.opportunity_score
    }


@app.route("/api/products")
def get_products():

    limit  = min(200, int(request.args.get("limit", 50)))
    offset = int(request.args.get("offset", 0))

    q = SessionLocal()

    try:

        products = (
            q.query(Product)
            .order_by(desc(Product.opportunity_score))
            .offset(offset)
            .limit(limit)
            .all()
        )

        return jsonify({
            "success": True,
            "products": [product_to_dict(p) for p in products]
        })

    finally:
        q.close()


# ─────────────────────────────────────────
# TRENDS API
# ─────────────────────────────────────────

@app.route("/api/trends")
def trends():

    data = get_top_trends(limit=50)

    return jsonify({
        "success": True,
        "trends": data
    })


@app.route("/api/trends/stats")
def trends_stats():
    return jsonify({
        "success": True,
        **get_trends_stats()
    })


# ─────────────────────────────────────────
# START SCHEDULER
# ─────────────────────────────────────────

def start_background_scheduler():

    log.info("Lancement du scheduler en arrière-plan")

    thread = threading.Thread(
        target=start_scheduler,
        daemon=True
    )

    thread.start()


# lancer le scheduler quand l'API démarre
start_background_scheduler()


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )