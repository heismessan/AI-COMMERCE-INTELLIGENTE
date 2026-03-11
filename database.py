"""
database.py
Connexion SQLAlchemy unique pour toute l'application
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime

from config import get_db_url


DATABASE_URL = get_db_url()

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=280
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


class Product(Base):

    __tablename__ = "products"

    id = Column(Integer, primary_key=True)

    title = Column(String(500))
    platform = Column(String(50))

    price = Column(Float)
    supplier_price = Column(Float)
    margin = Column(Float)

    sales = Column(Integer)
    reviews = Column(Integer)
    rating = Column(Float)

    trend_score = Column(Float)
    opportunity_score = Column(Float)

    affiliate_url = Column(String(1000))

    scraped_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)