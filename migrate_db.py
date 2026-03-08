"""
migrate_db.py
─────────────────────────────────────────────────────────
Script de migration MySQL pour AI Commerce Intelligence.

⚠️  Ce script supprime et recrée la table `products`.
    Toutes les données existantes seront perdues.
    Lance-le UNE seule fois pour corriger le schéma.

Usage :
    python migrate_db.py
"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime

# ── Configuration ──────────────────────────────────────────────────────────────
MYSQL_USER     = "root"
MYSQL_PASSWORD = "Attraction24"
MYSQL_HOST     = "127.0.0.1"
MYSQL_DB       = "ai_commerce"

DATABASE_URL = f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}"

# ── Modèle — doit toujours être identique à database.py ───────────────────────
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


# ── Migration ──────────────────────────────────────────────────────────────────
def migrate():
    print("Connexion à MySQL…")
    engine = create_engine(DATABASE_URL)

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Connexion OK")
    except Exception as e:
        print(f"❌ Impossible de se connecter : {e}")
        return

    print("Suppression de l'ancienne table `products`…")
    Base.metadata.drop_all(engine, tables=[Product.__table__])
    print("✅ Ancienne table supprimée")

    print("Création de la nouvelle table `products`…")
    Base.metadata.create_all(engine)
    print("✅ Nouvelle table créée avec les colonnes :")
    for col in Product.__table__.columns:
        print(f"   • {col.name} ({col.type})")

    Session = sessionmaker(bind=engine)
    session = Session()
    count = session.query(Product).count()
    session.close()
    print(f"\n🎉 Migration terminée — table vide et prête ({count} produits)")


if __name__ == "__main__":
    migrate()
