"""
config.py — AI Commerce Intelligence
─────────────────────────────────────────────────────────
Variables d'environnement centralisées.

En local    : crée un fichier .env dans backend/
En prod     : configure les variables dans Railway Dashboard
"""

import os

# ── Base de données ───────────────────────────────────────────────
# Railway injecte DATABASE_URL automatiquement pour MySQL
# Format : mysql+mysqlconnector://user:password@host:port/db

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "mysql+mysqlconnector://root:Attraction24@127.0.0.1/ai_commerce"  # fallback local
)

# Railway fournit aussi les variables séparées
MYSQL_USER     = os.environ.get("MYSQLUSER",     "root")
MYSQL_PASSWORD = os.environ.get("MYSQLPASSWORD", "Attraction24")
MYSQL_HOST     = os.environ.get("MYSQLHOST",     "127.0.0.1")
MYSQL_PORT     = os.environ.get("MYSQLPORT",     "3306")
MYSQL_DB       = os.environ.get("MYSQLDATABASE", "ai_commerce")

def get_db_url():
    """Retourne l'URL de connexion MySQL."""
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        # Railway préfixe parfois avec mysql:// au lieu de mysql+mysqlconnector://
        if db_url.startswith("mysql://"):
            db_url = db_url.replace("mysql://", "mysql+mysqlconnector://", 1)
        return db_url
    return f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"

# ── Auth ──────────────────────────────────────────────────────────
JWT_SECRET = os.environ.get("JWT_SECRET", "change_this_secret_in_production")

# ── Lemon Squeezy ─────────────────────────────────────────────────
LS_API_KEY      = os.environ.get("LS_API_KEY",      "")
LS_STORE_ID     = os.environ.get("LS_STORE_ID",     "308416")
LS_VARIANT_ID   = os.environ.get("LS_VARIANT_ID",   "1373877")
LS_WEBHOOK_SECRET = os.environ.get("LS_WEBHOOK_SECRET", "")

# ── Brevo Email ───────────────────────────────────────────────────
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
SENDER_EMAIL  = os.environ.get("SENDER_EMAIL",  "")
SENDER_NAME   = "AI Commerce Intelligence"

# ── URLs ──────────────────────────────────────────────────────────
# En prod Railway : https://ton-app.up.railway.app
APP_URL      = os.environ.get("APP_URL",      "http://localhost:5001")
API_URL      = os.environ.get("API_URL",      "http://localhost:5000")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5000")

# ── Ports ─────────────────────────────────────────────────────────
PORT      = int(os.environ.get("PORT",      5000))
AUTH_PORT = int(os.environ.get("AUTH_PORT", 5001))
