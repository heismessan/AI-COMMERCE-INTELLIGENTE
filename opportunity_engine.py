# backend/opportunity_engine.py

def calculate_opportunity(price, supplier_price, reviews=500, rating=4.5):
    """
    Calcule un score d'opportunité 0-10 basé sur :
    - marge
    - popularité simulée
    - note moyenne
    """
    # 1️⃣ marge
    margin_score = (price - supplier_price) / supplier_price  # ex : 50% = 0.5
    margin_score = min(margin_score, 2)  # on limite à 2 pour pas déformer le score

    # 2️⃣ popularité simulée
    # reviews et rating sont des données simulées
    demand_score = min(reviews / 1000, 1) * rating  # max 1*5=5

    # 3️⃣ calcul final
    opportunity_score = margin_score * 3 + demand_score  # pondération simple
    opportunity_score = round(min(opportunity_score, 10), 2)  # score max 10

    return opportunity_score