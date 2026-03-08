"""
database.py — AI Commerce Intelligence
─────────────────────────────────────────────────────────
Modèle Product + connexion MySQL.
"""

from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Product(Base):
    __tablename__ = "products"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    title             = Column(String(500), nullable=False)
    platform          = Column(String(50),  nullable=False)
    price             = Column(Float, default=0.0)
    supplier_price    = Column(Float, default=0.0)
    margin            = Column(Float, default=0.0)
    sales             = Column(Integer, default=0)
    reviews           = Column(Integer, default=0)
    rating            = Column(Float, default=0.0)
    trend_score       = Column(Float, default=0.0)
    opportunity_score = Column(Float, default=0.0)
    affiliate_url     = Column(String(1000), default="")   # ← lien affilié
    scraped_at        = Column(DateTime, default=datetime.utcnow)


# ── Connexion MySQL ────────────────────────────────────────────────
from config import get_db_url

engine = create_engine(
    get_db_url(),
    echo=False
)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine, checkfirst=True)
