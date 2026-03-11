"""
api.py
API principale Flask
"""

from flask import Flask, jsonify
from flask_cors import CORS
import threading

from database import SessionLocal, Product, init_db
from scheduler import start_scheduler

app = Flask(__name__)
CORS(app)


@app.route("/")
def health():
    return {"status": "AI Commerce Intelligence API running"}


@app.route("/products")
def products():

    session = SessionLocal()

    try:
        results = (
            session.query(Product)
            .order_by(Product.opportunity_score.desc())
            .limit(50)
            .all()
        )

        data = []

        for p in results:
            data.append({
                "id": p.id,
                "title": p.title,
                "platform": p.platform,
                "price": p.price,
                "margin": p.margin,
                "score": p.opportunity_score,
                "affiliate_url": p.affiliate_url
            })

        return jsonify(data)

    finally:
        session.close()


def start_background_services():

    thread = threading.Thread(
        target=start_scheduler,
        daemon=True
    )

    thread.start()


if __name__ == "__main__":

    print("Starting AI Commerce Intelligence API")

    init_db()

    start_background_services()

    app.run(
        host="0.0.0.0",
        port=5000
    )