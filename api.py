"""
api.py — AI Commerce Intelligence
API principale : Auth + Produits + Trends
"""

import os
import datetime

from functools import wraps

from flask import (
    Flask, jsonify, request, g
)

from flask_cors import CORS
from flask_bcrypt import Bcrypt

from sqlalchemy import (
    create_engine, Column, Integer, String,
    Boolean, DateTime, func, desc
)

from sqlalchemy.orm import declarative_base, sessionmaker

import jwt as pyjwt

from config import (
    get_db_url,
    JWT_SECRET
)

# IMPORTANT : correspond à ton database.py
from database import Product, SessionLocal

from trends_scraper import (
    get_top_trends,
    get_trends_stats
)

# ─────────────────────────────────────────
# APP
# ─────────────────────────────────────────

app = Flask(
    __name__,
    static_folder=".",
    static_url_path=""
)

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

    id = Column(Integer, primary_key=True, autoincrement=True)

    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    plan = Column(String(20), default="free")

    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    is_active = Column(Boolean, default=True)


Base.metadata.create_all(engine_users, checkfirst=True)

# ─────────────────────────────────────────
# AUTH HELPERS
# ─────────────────────────────────────────


def generate_token(user_id, plan):

    payload = {
        "user_id": user_id,
        "plan": plan,
        "exp": datetime.datetime.utcnow()
        + datetime.timedelta(days=7)
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

        token = auth.split(" ")[1]

        payload = verify_token(token)

        if not payload:
            return jsonify({"error": "Token invalide"}), 401

        g.user_id = payload["user_id"]
        g.plan = payload["plan"]

        return f(*args, **kwargs)

    return decorated


def require_pro(f):

    @wraps(f)
    def decorated(*args, **kwargs):

        auth = request.headers.get("Authorization", "")

        if not auth.startswith("Bearer "):
            return jsonify({"error": "Token manquant"}), 401

        token = auth.split(" ")[1]

        payload = verify_token(token)

        if not payload:
            return jsonify({"error": "Token invalide"}), 401

        if payload["plan"] != "pro":
            return jsonify({"error": "Plan Pro requis"}), 403

        g.user_id = payload["user_id"]
        g.plan = payload["plan"]

        return f(*args, **kwargs)

    return decorated


# ─────────────────────────────────────────
# STATIC PAGES
# ─────────────────────────────────────────

@app.route("/")
def home():
    return app.send_static_file("login.html")


@app.route("/login")
def login_page():
    return app.send_static_file("login.html")


@app.route("/register")
def register_page():
    return app.send_static_file("register.html")


@app.route("/dashboard")
def dashboard():
    return app.send_static_file("dashboard.html")


# ─────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────

@app.route("/health")
def health_check():
    return jsonify({"status": "AI Commerce Intelligence API running"})


# ─────────────────────────────────────────
# AUTH API
# ─────────────────────────────────────────

@app.route("/auth/register", methods=["POST"])
def register():

    data = request.get_json() or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    session = SessionUsers()

    try:

        if not email or not password:
            return jsonify({"error": "Email et mot de passe requis"}), 400

        if session.query(User).filter(User.email == email).first():
            return jsonify({"error": "Email déjà utilisé"}), 409

        hashed = bcrypt.generate_password_hash(password).decode("utf-8")

        user = User(
            email=email,
            password_hash=hashed
        )

        session.add(user)
        session.commit()

        return jsonify({"success": True})

    finally:
        session.close()


@app.route("/auth/login", methods=["POST"])
def login():

    data = request.get_json() or {}

    email = data.get("email", "").strip().lower()
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
# PRODUCTS
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


@app.route("/products/free")
def products_free():

    session = SessionLocal()

    try:

        products = (
            session.query(Product)
            .order_by(desc(Product.scraped_at))
            .limit(10)
            .all()
        )

        return jsonify({
            "plan": "free",
            "products": [product_to_dict(p) for p in products]
        })

    finally:
        session.close()


@app.route("/products/pro")
@require_pro
def products_pro():

    session = SessionLocal()

    try:

        products = (
            session.query(Product)
            .order_by(desc(Product.opportunity_score))
            .limit(100)
            .all()
        )

        return jsonify({
            "plan": "pro",
            "products": [product_to_dict(p) for p in products]
        })

    finally:
        session.close()


# ─────────────────────────────────────────
# STATS
# ─────────────────────────────────────────

@app.route("/api/stats")
def stats():

    session = SessionLocal()

    try:

        total = session.query(Product).count()

        avg_score = (
            session.query(func.avg(Product.opportunity_score)).scalar() or 0
        )

        return jsonify({
            "total_products": total,
            "avg_score": round(float(avg_score), 2)
        })

    finally:
        session.close()


# ─────────────────────────────────────────
# GOOGLE TRENDS
# ─────────────────────────────────────────

@app.route("/api/trends")
def trends():

    geo = request.args.get("geo", "")
    limit = int(request.args.get("limit", 50))

    trends = get_top_trends(geo_code=geo, limit=limit)

    return jsonify({
        "count": len(trends),
        "trends": trends
    })


@app.route("/api/trends/stats")
def trends_stats():
    return jsonify(get_trends_stats())


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )