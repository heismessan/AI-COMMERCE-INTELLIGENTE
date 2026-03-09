"""
database.py — AI Commerce Intelligence
─────────────────────────────────────────────────────────
Connexion base de données + modèle Product
Compatible Railway / MySQL / SQLAlchemy 2.x
"""

from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from config import get_db_url

# ─────────────────────────────────────────
# Base SQLAlchemy
# ─────────────────────────────────────────
Base = declarative_base()

# ─────────────────────────────────────────
# Modèle Product
# ─────────────────────────────────────────
class Product(Base):
    __tablename__ = "products"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    title             = Column(String(500), nullable=False)
    platform          = Column(String(50), nullable=False)

    price             = Column(Float, default=0.0)
    supplier_price    = Column(Float, default=0.0)
    margin            = Column(Float, default=0.0)

    sales             = Column(Integer, default=0)
    reviews           = Column(Integer, default=0)
    rating            = Column(Float, default=0.0)

    trend_score       = Column(Float, default=0.0)
    opportunity_score = Column(Float, default=0.0)

    affiliate_url     = Column(String(1000), default="")

    scraped_at        = Column(DateTime, default=datetime.utcnow)


# ─────────────────────────────────────────
# Connexion base de données
# ─────────────────────────────────────────
DATABASE_URL = get_db_url()

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=280,
    echo=False
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# ─────────────────────────────────────────
# Création automatique des tables
# ─────────────────────────────────────────
def init_db():
    Base.metadata.create_all(bind=engine)


# ─────────────────────────────────────────
# Dependency FastAPI
# ─────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Initialisation automatique
init_db()