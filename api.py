"""
api.py — AI Commerce Intelligence
Service unique : API produits + Auth + Static files
"""

import os
import datetime
import hashlib
import hmac
import json

from flask import Flask, jsonify, request, redirect, send_from_directory
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    Boolean, DateTime, Text, func, desc
)
from sqlalchemy.orm import declarative_base, sessionmaker
import jwt as pyjwt

from config import (
    get_db_url, JWT_SECRET,
    LS_API_KEY, LS_STORE_ID, LS_VARIANT_ID, LS_WEBHOOK_SECRET,
    APP_URL
)
from database import Product, Session as ProductSession
from email_service import (
    send_confirmation_email, send_welcome_email,
    generate_verification_token, token_expiry
)
from trends_scraper import get_top_trends, get_trends_stats

# ── App ───────────────────────────────────────────────────────────
app    = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)
bcrypt = Bcrypt(app)

# ── Base de données Users ─────────────────────────────────────────
Base          = declarative_base()
engine_users  = create_engine(get_db_url(), echo=False)
SessionUsers  = sessionmaker(bind=engine_users)

class User(Base):
    __tablename__ = "users"
    id             = Column(Integer,     primary_key=True, autoincrement=True)
    email          = Column(String(255), unique=True, nullable=False)
    password_hash  = Column(String(255), nullable=False)
    plan           = Column(String(20),  default="free")
    ls_customer_id = Column(String(100), default="")
    ls_sub_id      = Column(String(100), default="")
    pro_until      = Column(DateTime,    nullable=True)
    created_at     = Column(DateTime,    default=datetime.datetime.utcnow)
    is_active      = Column(Boolean,     default=True)
    is_verified    = Column(Boolean,     default=False)
    verify_token   = Column(String(100), default="")
    verify_expiry  = Column(DateTime,    nullable=True)

Base.metadata.create_all(engine_users, checkfirst=True)

# ── Helpers Auth ──────────────────────────────────────────────────
def generate_token(user_id, plan):
    payload = {
        "user_id": user_id,
        "plan":    plan,
        "exp":     datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm="HS256")

def verify_token(token):
    try:
        return pyjwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return None

def get_current_user():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    payload = verify_token(token)
    if not payload:
        return None
    session = SessionUsers()
    try:
        return session.query(User).filter_by(id=payload["user_id"]).first()
    finally:
        session.close()

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"success": False, "error": "Token manquant."}), 401
        payload = decode_token(auth.split(" ")[1])
        if not payload:
            return jsonify({"success": False, "error": "Token invalide ou expiré."}), 401
        g.user_id = payload["user_id"]
        g.plan    = payload["plan"]
        return f(*args, **kwargs)
    return decorated

# ── Pages statiques ───────────────────────────────────────────────
@app.route('/')
def index():
    return app.send_static_file('login.html')

@app.route('/dashboard')
def dashboard():
    return app.send_static_file('dashboard.html')

# ══════════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ══════════════════════════════════════════════════════════════════


@app.route("/auth/register", methods=["POST"])
def register():
    data     = request.get_json() or {}
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or "@" not in email:
        return jsonify({"success": False, "error": "Email invalide."}), 400
    if len(password) < 6:
        return jsonify({"success": False, "error": "Mot de passe trop court (6 caractères min)."}), 400

    session = SessionUsers()
    try:
        if session.query(User).filter(User.email == email).first():
            return jsonify({"success": False, "error": "Email déjà utilisé."}), 409

        hashed        = bcrypt.generate_password_hash(password).decode("utf-8")
        verify_tok    = generate_verification_token()
        user          = User(
            email        = email,
            password_hash= hashed,
            plan         = "free",
            is_verified  = False,
            verify_token = verify_tok,
            verify_expiry= token_expiry(),
        )
        session.add(user)
        session.commit()

        # Envoyer l'email de confirmation
        email_result = send_confirmation_email(email, verify_tok)
        if not email_result["success"]:
            # On garde le compte mais on prévient
            return jsonify({
                "success": True,
                "verified": False,
                "message": "Compte créé mais l'envoi de l'email a échoué. Contacte le support.",
                "email_error": email_result["error"],
            }), 201

        return jsonify({
            "success":  True,
            "verified": False,
            "message":  f"Compte créé ! Un email de confirmation a été envoyé à {email}.",
        }), 201

    except Exception as e:
        session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        session.close()



@app.route("/auth/login", methods=["POST"])
def login():
    data     = request.get_json() or {}
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")

    session = SessionUsers()
    try:
        user = session.query(User).filter(User.email == email).first()
        if not user or not bcrypt.check_password_hash(user.password_hash, password):
            return jsonify({"success": False, "error": "Email ou mot de passe incorrect."}), 401

        # Vérifier si l'email est confirmé
        if not user.is_verified:
            return jsonify({
                "success":  False,
                "error":    "Email non confirmé. Vérifie ta boîte mail et clique sur le lien de confirmation.",
                "unverified": True,
                "email":    email,
            }), 403

        # Vérifier expiration Pro
        if user.plan == "pro" and user.pro_until and user.pro_until < datetime.datetime.utcnow():
            user.plan = "free"
            session.commit()

        token = generate_token(user.id, user.plan)
        return jsonify({
            "success": True,
            "token":   token,
            "user": {
                "id":        user.id,
                "email":     user.email,
                "plan":      user.plan,
                "pro_until": user.pro_until.isoformat() if user.pro_until else None,
            },
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        session.close()



@app.route("/auth/me", methods=["GET"])
@require_auth
def me():
    session = SessionUsers()
    try:
        user = session.query(User).filter(User.id == g.user_id).first()
        if not user:
            return jsonify({"success": False, "error": "Introuvable."}), 404
        return jsonify({
            "success": True,
            "user": {
                "id":        user.id,
                "email":     user.email,
                "plan":      user.plan,
                "pro_until": user.pro_until.isoformat() if user.pro_until else None,
                "created_at":user.created_at.isoformat(),
            }
        })
    finally:
        session.close()


# ══════════════════════════════════════════════════════════════════
#  LEMON SQUEEZY — PAIEMENT
# ══════════════════════════════════════════════════════════════════

LS_HEADERS = {
    "Authorization": f"Bearer {LS_API_KEY}",
    "Accept":        "application/vnd.api+json",
    "Content-Type":  "application/vnd.api+json",
}


@app.route("/auth/create-checkout", methods=["POST"])
@require_auth
def create_checkout():
    """
    Crée une session Lemon Squeezy Checkout.
    Retourne l'URL de paiement à ouvrir dans le navigateur.
    """
    session = SessionUsers()
    try:
        user = session.query(User).filter(User.id == g.user_id).first()

        payload = {
            "data": {
                "type": "checkouts",
                "attributes": {
                    "checkout_data": {
                        "email": user.email,
                        "custom": {"user_id": str(user.id)},
                    },
                    "product_options": {
                        "redirect_url":      f"{APP_URL}/auth/payment-success",
                    },
                },
                "relationships": {
                    "store": {
                        "data": {"type": "stores", "id": LS_STORE_ID}
                    },
                    "variant": {
                        "data": {"type": "variants", "id": LS_VARIANT_ID}
                    },
                },
            }
        }

        r = requests.post(
            "https://api.lemonsqueezy.com/v1/checkouts",
            headers=LS_HEADERS,
            json=payload,
            timeout=10,
        )

        if r.status_code not in (200, 201):
            return jsonify({"success": False, "error": f"Lemon Squeezy: {r.text}"}), 500

        checkout_url = r.json()["data"]["attributes"]["url"]
        return jsonify({"success": True, "checkout_url": checkout_url})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        session.close()



@app.route("/auth/payment-success", methods=["GET"])
def payment_success():
    return jsonify({
        "success": True,
        "message": "Paiement réussi ! Votre plan Pro est activé. Reconnectez-vous."
    })


# ══════════════════════════════════════════════════════════════════
#  LEMON SQUEEZY — WEBHOOK
#  À configurer dans LS → Settings → Webhooks
#  URL : http://TON_SERVEUR/auth/ls-webhook
#  Events : order_created, subscription_created,
#            subscription_cancelled, subscription_expired
# ══════════════════════════════════════════════════════════════════

def verify_ls_signature(payload: bytes, signature: str) -> bool:
    """Vérifie que le webhook vient bien de Lemon Squeezy."""
    if not LS_WEBHOOK_SECRET:
        return True   # désactivé en dev
    digest = hmac.new(
        LS_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(digest, signature)



@app.route("/auth/confirm-email", methods=["GET"])
def confirm_email():
    """
    Confirmation de l'email via le lien reçu.
    GET /auth/confirm-email?token=xxx
    """
    token = request.args.get("token", "").strip()
    if not token:
        return jsonify({"success": False, "error": "Token manquant."}), 400

    session = SessionUsers()
    try:
        user = session.query(User).filter(User.verify_token == token).first()
        if not user:
            return jsonify({"success": False, "error": "Lien invalide ou déjà utilisé."}), 400

        if user.verify_expiry and user.verify_expiry < datetime.datetime.utcnow():
            return jsonify({
                "success": False,
                "error":   "Lien expiré (24h). Reconnecte-toi pour recevoir un nouveau lien.",
                "expired": True,
                "email":   user.email,
            }), 400

        # Activer le compte
        user.is_verified  = True
        user.verify_token = ""
        session.commit()

        # Envoyer l'email de bienvenue
        send_welcome_email(user.email)

        # Rediriger vers login.html avec message de succès
        from flask import redirect
        return redirect(f"http://localhost:5000/login.html?confirmed=1")

    except Exception as e:
        session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        session.close()



@app.route("/auth/resend-confirmation", methods=["POST"])
def resend_confirmation():
    """
    Renvoie un email de confirmation.
    Body JSON : { email }
    """
    data  = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    if not email:
        return jsonify({"success": False, "error": "Email requis."}), 400

    session = SessionUsers()
    try:
        user = session.query(User).filter(User.email == email).first()
        if not user:
            # Sécurité : ne pas révéler si l'email existe
            return jsonify({"success": True, "message": "Si ce compte existe, un email a été envoyé."})

        if user.is_verified:
            return jsonify({"success": False, "error": "Ce compte est déjà vérifié."}), 400

        # Générer un nouveau token
        user.verify_token  = generate_verification_token()
        user.verify_expiry = token_expiry()
        session.commit()

        result = send_confirmation_email(email, user.verify_token)
        if result["success"]:
            return jsonify({"success": True, "message": "Email de confirmation renvoyé !"})
        else:
            return jsonify({"success": False, "error": result["error"]}), 500

    except Exception as e:
        session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        session.close()



@app.route("/auth/ls-webhook", methods=["POST"])
def ls_webhook():
    payload   = request.get_data()
    signature = request.headers.get("X-Signature", "")

    if not verify_ls_signature(payload, signature):
        return jsonify({"error": "Signature invalide."}), 403

    event = request.get_json()
    etype = event.get("meta", {}).get("event_name", "")
    data  = event.get("data", {}).get("attributes", {})

    # Récupérer l'user_id passé dans custom data
    user_id = (
        event.get("meta", {}).get("custom_data", {}).get("user_id")
        or data.get("first_order_item", {}).get("custom_data", {}).get("user_id")
    )

    session = SessionUsers()
    try:
        user = None
        if user_id:
            user = session.query(User).filter(User.id == int(user_id)).first()
        if not user:
            email = data.get("user_email", "")
            if email:
                user = session.query(User).filter(User.email == email).first()

        if not user:
            return jsonify({"received": True, "warning": "User non trouvé"}), 200

        if etype in ("order_created", "subscription_created"):
            # Activer Pro
            user.plan          = "pro"
            user.ls_customer_id = str(data.get("customer_id", ""))
            user.ls_sub_id      = str(event.get("data", {}).get("id", ""))
            user.pro_until      = None   # actif tant que l'abo est actif
            print(f"✅ Pro activé pour {user.email}")

        elif etype in ("subscription_cancelled", "subscription_expired"):
            # Désactiver Pro
            user.plan = "free"
            print(f"⚠️  Pro désactivé pour {user.email}")

        session.commit()

    except Exception as e:
        session.rollback()
        print(f"❌ Webhook error: {e}")
    finally:
        session.close()

    return jsonify({"received": True})


# ══════════════════════════════════════════════════════════════════
#  PRODUITS AVEC CONTRÔLE DE PLAN
# ══════════════════════════════════════════════════════════════════

def product_to_dict(p, hide_score=False):
    return {
        "id":                p.id,
        "title":             p.title,
        "platform":          p.platform,
        "price":             p.price,
        "margin":            round(p.margin * 100, 1),
        "sales":             p.sales,
        "reviews":           p.reviews,
        "rating":            p.rating,
        "opportunity_score": p.opportunity_score if not hide_score else None,
        "affiliate_url":     p.affiliate_url or "",
        "scraped_at":        p.scraped_at.isoformat() if p.scraped_at else None,
    }



@app.route("/products/free", methods=["GET"])
def products_free():
    """10 produits sans scores — aucune auth requise."""
    session = ProductSession()
    try:
        products = (
            session.query(Product)
            .order_by(desc(Product.scraped_at))
            .limit(10).all()
        )
        return jsonify({
            "success":  True,
            "plan":     "free",
            "products": [product_to_dict(p, hide_score=True) for p in products],
        })
    finally:
        session.close()



@app.route("/products/pro", methods=["GET"])
@require_pro
def products_pro():
    """Tous les produits avec scores — Pro uniquement."""
    session  = ProductSession()
    try:
        page     = max(1, int(request.args.get("page", 1)))
        per_page = min(100, max(1, int(request.args.get("per_page", 20))))
        platform = request.args.get("platform", "").strip()
        sort_by  = request.args.get("sort", "opportunity_score")

        sort_map = {
            "opportunity_score": desc(Product.opportunity_score),
            "rating":            desc(Product.rating),
            "sales":             desc(Product.sales),
            "price":             Product.price,
        }

        query = session.query(Product)
        if platform:
            query = query.filter(Product.platform == platform)
        query    = query.order_by(sort_map.get(sort_by, desc(Product.opportunity_score)))
        total    = query.count()
        products = query.offset((page - 1) * per_page).limit(per_page).all()

        return jsonify({
            "success":  True,
            "plan":     "pro",
            "total":    total,
            "page":     page,
            "pages":    (total + per_page - 1) // per_page,
            "products": [product_to_dict(p) for p in products],
        })
    finally:
        session.close()



@app.route("/products/export", methods=["GET"])
@require_pro
def export_csv():
    """Export CSV complet — Pro uniquement."""
    import csv, io
    session = ProductSession()
    try:
        products = session.query(Product).order_by(desc(Product.opportunity_score)).all()
        output   = io.StringIO()
        writer   = csv.writer(output)
        writer.writerow(["ID","Titre","Plateforme","Prix","Marge%",
                         "Ventes","Avis","Note","Score","URL Affilié"])
        for p in products:
            writer.writerow([
                p.id, p.title, p.platform, p.price,
                round(p.margin*100,1), p.sales, p.reviews,
                p.rating, p.opportunity_score, p.affiliate_url or ""
            ])
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=products_pro.csv"}
        )
    finally:
        session.close()


# ══════════════════════════════════════════════════════════════════
#  LANCEMENT
# ══════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════
#  API ROUTES
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


# ── AUTH ROUTES ─────────────────────────────────────────────────

# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", debug=False, port=port)
