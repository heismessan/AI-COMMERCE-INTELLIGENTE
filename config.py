"""
config.py — AI Commerce Intelligence
Gestion centralisée de la configuration
Compatible Local + Railway
"""

import os


def get_db_url():
    db_url = os.getenv("DATABASE_URL")

    if db_url:
        if db_url.startswith("mysql://"):
            db_url = db_url.replace(
                "mysql://",
                "mysql+mysqlconnector://",
                1
            )
        return db_url

    user = os.getenv("MYSQLUSER", "root")
    password = os.getenv("MYSQLPASSWORD", "")
    host = os.getenv("MYSQLHOST", "127.0.0.1")
    port = os.getenv("MYSQLPORT", "3306")
    db = os.getenv("MYSQLDATABASE", "ai_commerce")

    return f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{db}"


JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME")


BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
SENDER_NAME = "AI Commerce Intelligence"


APP_URL = os.getenv("APP_URL", "http://localhost:5000")

PORT = int(os.getenv("PORT", 5000))