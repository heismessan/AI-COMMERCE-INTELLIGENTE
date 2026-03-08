"""
scoring_ai.py — AI Commerce Intelligence
─────────────────────────────────────────────────────────
Système de scoring multi-critères sur 10 points.

Critères pondérés :
  • Marge bénéficiaire    → 30%
  • Demande (sales)       → 25%
  • Preuve sociale        → 20%  (reviews)
  • Qualité produit       → 15%  (rating)
  • Tendance marché       → 10%  (trend_score)

Chaque critère est normalisé sur [0, 1] avant pondération,
ce qui garantit une distribution réaliste des scores (pas
tout à 10/10).
"""

import math
import random


# ══════════════════════════════════════════════════════════════════
#  NORMALISATION — chaque critère → valeur entre 0 et 1
# ══════════════════════════════════════════════════════════════════

def normalize_margin(margin: float) -> float:
    """
    margin = (price - supplier) / supplier  (ex: 0.8 = 80%)
    Bonne marge : 50-150%. On plafonne à 200%.
    Courbe logarithmique pour ne pas écraser les petites marges.
    """
    if margin <= 0:
        return 0.0
    # log pour aplatir les très hautes marges
    score = math.log1p(margin) / math.log1p(2.0)   # log(1+2) = plafond 200%
    return round(min(score, 1.0), 4)


def normalize_sales(sales: int) -> float:
    """
    0 ventes → 0.0 | 1000+ ventes → ~1.0
    Courbe racine carrée : récompense la croissance initiale.
    """
    if sales <= 0:
        return 0.0
    score = math.sqrt(sales) / math.sqrt(1000)
    return round(min(score, 1.0), 4)


def normalize_reviews(reviews: int) -> float:
    """
    0 avis → 0.0 | 500+ avis → ~1.0
    Logarithmique : les premiers avis comptent beaucoup.
    """
    if reviews <= 0:
        return 0.0
    score = math.log1p(reviews) / math.log1p(500)
    return round(min(score, 1.0), 4)


def normalize_rating(rating: float) -> float:
    """
    0.0 → 0.0 | 5.0 → 1.0
    Note < 3.0 pénalisée fortement.
    """
    if rating <= 0:
        return 0.0
    if rating < 3.0:
        return round((rating / 3.0) * 0.3, 4)   # < 3 étoiles = max 30%
    score = (rating - 3.0) / 2.0                 # 3.0→0.0, 5.0→1.0
    return round(min(score, 1.0), 4)


def normalize_trend(trend_score: float) -> float:
    """trend_score est déjà entre 0 et 1."""
    return round(min(max(trend_score, 0.0), 1.0), 4)


# ══════════════════════════════════════════════════════════════════
#  SCORING PRINCIPAL
# ══════════════════════════════════════════════════════════════════

# Poids des critères (somme = 1.0)
WEIGHTS = {
    "margin":  0.30,
    "sales":   0.25,
    "reviews": 0.20,
    "rating":  0.15,
    "trend":   0.10,
}

def score_with_local_ai(
    title: str,
    price: float,
    supplier_price: float,
    sales: int        = 0,
    reviews: int      = 0,
    rating: float     = 0.0,
    trend_score: float = None,
) -> float:
    """
    Calcule un score d'opportunité entre 0.0 et 10.0.

    Paramètres :
        title          → non utilisé pour l'instant (prévu pour NLP)
        price          → prix de vente
        supplier_price → prix fournisseur estimé
        sales          → volume de ventes estimé
        reviews        → nombre d'avis
        rating         → note moyenne (0-5)
        trend_score    → score de tendance (0-1), aléatoire si None

    Retourne :
        float entre 0.0 et 10.0, arrondi à 2 décimales
    """
    # Calcul de la marge
    margin = (price - supplier_price) / max(supplier_price, 0.01)

    # Trend aléatoire si non fourni (données simulées)
    if trend_score is None:
        trend_score = random.uniform(0.4, 0.95)

    # Normalisation de chaque critère
    n_margin  = normalize_margin(margin)
    n_sales   = normalize_sales(sales)
    n_reviews = normalize_reviews(reviews)
    n_rating  = normalize_rating(rating)
    n_trend   = normalize_trend(trend_score)

    # Score pondéré [0, 1]
    weighted = (
        n_margin  * WEIGHTS["margin"]  +
        n_sales   * WEIGHTS["sales"]   +
        n_reviews * WEIGHTS["reviews"] +
        n_rating  * WEIGHTS["rating"]  +
        n_trend   * WEIGHTS["trend"]
    )

    # Mise à l'échelle [0, 10]
    final_score = round(weighted * 10, 2)

    return final_score


# ══════════════════════════════════════════════════════════════════
#  RECALCUL EN MASSE (pour mettre à jour les produits existants)
# ══════════════════════════════════════════════════════════════════

def recalculate_all_scores():
    """
    Recalcule l'opportunity_score de tous les produits en base
    avec le nouveau système de scoring.

    Usage :
        python scoring_ai.py
    """
    from database import Session, Product

    session = Session()
    try:
        products = session.query(Product).all()
        print(f"Recalcul du scoring pour {len(products)} produits…\n")

        scores = []
        for p in products:
            margin = (p.price - p.supplier_price) / max(p.supplier_price, 0.01)
            new_score = score_with_local_ai(
                title          = p.title,
                price          = p.price,
                supplier_price = p.supplier_price,
                sales          = p.sales   or 0,
                reviews        = p.reviews or 0,
                rating         = p.rating  or 0.0,
                trend_score    = p.trend_score,
            )
            p.opportunity_score = new_score
            scores.append(new_score)

        session.commit()

        # Statistiques de distribution
        if scores:
            avg   = sum(scores) / len(scores)
            mn    = min(scores)
            mx    = max(scores)
            # Histogramme simplifié
            buckets = [0] * 10
            for s in scores:
                idx = min(int(s), 9)
                buckets[idx] += 1

            print(f"{'─'*40}")
            print(f"  Produits recalculés : {len(scores)}")
            print(f"  Score min / moy / max : {mn:.2f} / {avg:.2f} / {mx:.2f}")
            print(f"\n  Distribution :")
            for i, count in enumerate(buckets):
                bar   = '█' * count
                label = f"  {i}-{i+1}"
                print(f"  {label}  {bar} ({count})")
            print(f"{'─'*40}")
            print("✅ Scores mis à jour en base.")

    except Exception as e:
        session.rollback()
        print(f"❌ Erreur : {e}")
        raise
    finally:
        session.close()


# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    recalculate_all_scores()
