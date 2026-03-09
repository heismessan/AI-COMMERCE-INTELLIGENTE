"""
config.py — AI Commerce Intelligence
─────────────────────────────────────────────────────────
Gestion centralisée des variables d'environnement
Compatible Railway / Local
"""

import os


# ─────────────────────────────────────────
# Base de données
# ─────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL")

MYSQL_USER = os.getenv("MYSQLUSER", "root")
MYSQL_PASSWORD = os.getenv("MYSQLPASSWORD", "Attraction24")
MYSQL_HOST = os.getenv("MYSQLHOST", "127.0.0.1")
MYSQL_PORT = os.getenv("MYSQLPORT", "3306")
MYSQL_DB = os.getenv("MYSQLDATABASE", "ai_commerce")


def get_db_url():
    """
    Retourne l'URL de connexion MySQL compatible SQLAlchemy
    """

    db_url = os.getenv("DATABASE_URL")

    if db_url:
        # Railway met souvent mysql://
        if db_url.startswith("mysql://"):
            db_url = db_url.replace(
                "mysql://",
                "mysql+mysqlconnector://",
                1
            )
        return db_url

    # fallback local
    return f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"


# ─────────────────────────────────────────
# Authentification JWT
# ─────────────────────────────────────────

JWT_SECRET = os.getenv(
    "JWT_SECRET",
    "CHANGE_THIS_SECRET_IN_PRODUCTION"
)


# ─────────────────────────────────────────
# Lemon Squeezy (paiements)
# ─────────────────────────────────────────

LS_API_KEY = os.getenv("LS_API_KEY", "")
LS_STORE_ID = os.getenv("LS_STORE_ID", "")
LS_VARIANT_ID = os.getenv("LS_VARIANT_ID", "")
LS_WEBHOOK_SECRET = os.getenv("LS_WEBHOOK_SECRET", "")


# ─────────────────────────────────────────
# Brevo (email)
# ─────────────────────────────────────────

BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
SENDER_NAME = "AI Commerce Intelligence"


# ─────────────────────────────────────────
# URLs application
# ─────────────────────────────────────────

APP_URL = os.getenv(
    "APP_URL",
    "https://ai-commerce-intelligente-production.up.railway.app"
)

API_URL = os.getenv(
    "API_URL",
    "https://ai-commerce-intelligente-production.up.railway.app"
)

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "https://ai-commerce-intelligente-production.up.railway.app"
)


# ─────────────────────────────────────────
# Ports
# ─────────────────────────────────────────

PORT = int(os.getenv("PORT", 5000))
AUTH_PORT = int(os.getenv("AUTH_PORT", 5001))