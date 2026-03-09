"""
api.py — AI Commerce Intelligence
─────────────────────────────────────────────────────────
API Flask pour exposer les données produits.

Endpoints :
  GET  /api/products          → tous les produits (pagination)
  GET  /api/products/top      → top produits par opportunity_score
  GET  /api/products/search   → recherche par titre
  GET  /api/products/<id>     → un produit par ID
  GET  /api/stats             → statistiques globales
  GET  /api/platforms         → liste des plateformes disponibles

Prérequis :
    pip install flask flask-cors

Usage :
    python api.py
    → http://localhost:5000
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy import func, desc
from database import Session, Product

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

@app.route('/')
def index():
    return app.send_static_file('login.html')

@app.route('/dashboard')
def dashboard():
    return app.send_static_file('dashboard.html')


# ══════════════════════════════════════════════════════════════════
#  HELPER
# ══════════════════════════════════════════════════════════════════

def product_to_dict(p):
    return {
        "id":                p.id,
        "title":             p.title,
        "platform":          p.platform,
        "price":             p.price,
        "supplier_price":    p.supplier_price,
        "margin":            round(p.margin * 100, 1),
        "sales":             p.sales,
        "reviews":           p.reviews,
        "rating":            p.rating,
        "trend_score":       p.trend_score,
        "opportunity_score": p.opportunity_score,
        "affiliate_url":     p.affiliate_url or "",
        "scraped_at":        p.scraped_at.isoformat() if p.scraped_at else None,
    }


# ══════════════════════════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════════════════════════

@app.route("/api/products", methods=["GET"])
def get_products():
    """
    Retourne tous les produits avec pagination et filtres.

    Query params :
      page       (int, défaut 1)
      per_page   (int, défaut 20, max 100)
      platform   (str) → filtre par plateforme ex: Amazon
      min_score  (float) → score minimum
      sort       (str)   → opportunity_score | rating | price | sales
    """
    session = Session()
    try:
        page      = max(1, int(request.args.get("page", 1)))
        per_page  = min(100, max(1, int(request.args.get("per_page", 20))))
        platform  = request.args.get("platform", "").strip()
        min_score = float(request.args.get("min_score", 0))
        sort_by   = request.args.get("sort", "opportunity_score")

        query = session.query(Product).filter(
            Product.opportunity_score >= min_score
        )

        if platform:
            query = query.filter(Product.platform == platform)

        sort_map = {
            "opportunity_score": desc(Product.opportunity_score),
            "rating":            desc(Product.rating),
            "price":             Product.price,
            "sales":             desc(Product.sales),
        }
        query = query.order_by(sort_map.get(sort_by, desc(Product.opportunity_score)))

        total    = query.count()
        products = query.offset((page - 1) * per_page).limit(per_page).all()

        return jsonify({
            "success":  True,
            "total":    total,
            "page":     page,
            "per_page": per_page,
            "pages":    (total + per_page - 1) // per_page,
            "products": [product_to_dict(p) for p in products],
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        session.close()


@app.route("/api/products/top", methods=["GET"])
def get_top_products():
    """
    Retourne les N meilleurs produits par opportunity_score.

    Query params :
      limit    (int, défaut 10)
      platform (str) → filtre optionnel
    """
    session = Session()
    try:
        limit    = min(50, max(1, int(request.args.get("limit", 10))))
        platform = request.args.get("platform", "").strip()

        query = session.query(Product).order_by(desc(Product.opportunity_score))
        if platform:
            query = query.filter(Product.platform == platform)

        products = query.limit(limit).all()

        return jsonify({
            "success":  True,
            "products": [product_to_dict(p) for p in products],
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        session.close()


@app.route("/api/products/search", methods=["GET"])
def search_products():
    """
    Recherche des produits par mot-clé dans le titre.

    Query params :
      q        (str, requis)
      limit    (int, défaut 20)
      platform (str) → filtre optionnel
    """
    session = Session()
    try:
        q        = request.args.get("q", "").strip()
        limit    = min(50, max(1, int(request.args.get("limit", 20))))
        platform = request.args.get("platform", "").strip()

        if not q:
            return jsonify({"success": False, "error": "Paramètre 'q' requis."}), 400

        query = session.query(Product).filter(Product.title.ilike(f"%{q}%"))

        if platform:
            query = query.filter(Product.platform == platform)

        query    = query.order_by(desc(Product.opportunity_score)).limit(limit)
        products = query.all()

        return jsonify({
            "success":  True,
            "query":    q,
            "count":    len(products),
            "products": [product_to_dict(p) for p in products],
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        session.close()


@app.route("/api/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    """Retourne un produit par son ID."""
    session = Session()
    try:
        product = session.query(Product).filter(Product.id == product_id).first()
        if not product:
            return jsonify({"success": False, "error": "Produit introuvable."}), 404
        return jsonify({"success": True, "product": product_to_dict(product)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        session.close()


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Statistiques globales de la base de données."""
    session = Session()
    try:
        total      = session.query(Product).count()
        avg_score  = session.query(func.avg(Product.opportunity_score)).scalar() or 0
        avg_price  = session.query(func.avg(Product.price)).scalar() or 0
        avg_rating = session.query(func.avg(Product.rating)).scalar() or 0
        avg_margin = session.query(func.avg(Product.margin)).scalar() or 0

        by_platform = (
            session.query(Product.platform, func.count(Product.id))
            .group_by(Product.platform)
            .all()
        )

        best = (
            session.query(Product)
            .order_by(desc(Product.opportunity_score))
            .first()
        )

        return jsonify({
            "success":        True,
            "total_products": total,
            "avg_score":      round(float(avg_score), 2),
            "avg_price":      round(float(avg_price), 2),
            "avg_rating":     round(float(avg_rating), 2),
            "avg_margin_pct": round(float(avg_margin) * 100, 1),
            "by_platform":    {row[0]: row[1] for row in by_platform},
            "best_product":   product_to_dict(best) if best else None,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        session.close()


@app.route("/api/platforms", methods=["GET"])
def get_platforms():
    """Liste des plateformes disponibles dans la base."""
    session = Session()
    try:
        platforms = session.query(Product.platform).distinct().all()
        return jsonify({
            "success":   True,
            "platforms": [p[0] for p in platforms],
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        session.close()


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "name":    "AI Commerce Intelligence API",
        "version": "1.0",
        "endpoints": {
            "GET /api/products":           "Tous les produits (pagination, filtres)",
            "GET /api/products/top":       "Top produits par score",
            "GET /api/products/search?q=": "Recherche par titre",
            "GET /api/products/<id>":      "Produit par ID",
            "GET /api/stats":              "Statistiques globales",
            "GET /api/platforms":          "Plateformes disponibles",
        }
    })


# ══════════════════════════════════════════════════════════════════
#  LANCEMENT
# ══════════════════════════════════════════════════════════════════

# ── TRENDS (Pro) ─────────────────────────────────────────────────

@app.route("/api/trends", methods=["GET"])
def api_trends():
    """
    Retourne les tendances Google Trends.
    Params : geo (code pays), limit, category
    """
    geo      = request.args.get("geo", "")        # "" = mondial, "TG", "FR"...
    limit    = min(100, int(request.args.get("limit", 50)))
    category = request.args.get("category", "")
    trends   = get_top_trends(geo_code=geo, limit=limit, category=category)
    return jsonify({"success": True, "count": len(trends), "trends": trends})


@app.route("/api/trends/stats", methods=["GET"])
def api_trends_stats():
    """Statistiques des tendances."""
    return jsonify({"success": True, **get_trends_stats()})


@app.route("/api/trends/zones", methods=["GET"])
def api_trends_zones():
    """Liste des zones géographiques disponibles."""
    zones = [
        {"code": "",   "label": "🌍 Mondial"},
        {"code": "TG", "label": "🇹🇬 Togo"},
        {"code": "SN", "label": "🇸🇳 Sénégal"},
        {"code": "CI", "label": "🇨🇮 Côte d'Ivoire"},
        {"code": "FR", "label": "🇫🇷 France"},
        {"code": "CM", "label": "🇨🇲 Cameroun"},
    ]
    return jsonify({"success": True, "zones": zones})


if __name__ == "__main__":
    print("═" * 45)
    print("  AI Commerce Intelligence — API")
    print("  http://localhost:5000")
    print("═" * 45)
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", debug=False, port=port)
