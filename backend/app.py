"""
Mexico Limited — AI Agent Backend
Entry point: registers all blueprints, starts the cron scheduler,
and serves the Flask application.
"""

import json
import logging
import sys

from flask import Flask, request, jsonify
from flask_cors import CORS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """Application factory."""
    app = Flask(__name__)
    CORS(app)

    # ── Register Blueprints ───────────────────────────────────────
    from api.webhooks.lead_webhook import lead_webhook_bp
    from api.webhooks.whatsapp_webhook import whatsapp_webhook_bp

    app.register_blueprint(lead_webhook_bp)
    app.register_blueprint(whatsapp_webhook_bp)

    # ── Existing Service Matching Feature ─────────────────────────
    # (Preserved from the original demo)
    try:
        with open("services.json", "r", encoding="utf-8") as f:
            services = json.load(f)

        documents = [
            f"{s['name']} {s['category']} {s['description']}" for s in services
        ]
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(documents)

        @app.route("/api/match", methods=["POST"])
        def match_services():
            data = request.json
            if not data or "needs" not in data:
                return jsonify({"error": "Please provide entrepreneur needs"}), 400

            query = data["needs"]
            query_vec = vectorizer.transform([query])
            similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
            related_docs_indices = similarities.argsort()[::-1]

            results = []
            for i in related_docs_indices:
                score = similarities[i]
                if score > 0.05:
                    service_match = services[i].copy()
                    service_match["match_score"] = round(score * 100, 2)
                    results.append(service_match)

            if not results and len(related_docs_indices) >= 2:
                for i in related_docs_indices[:2]:
                    service_match = services[i].copy()
                    service_match["match_score"] = round(
                        similarities[i] * 100, 2
                    )
                    results.append(service_match)

            return jsonify({"matches": results[:3]})

    except FileNotFoundError:
        logger.warning("services.json not found, /api/match will not be available.")

    # ── Health Check ──────────────────────────────────────────────

    @app.route("/api/health", methods=["GET"])
    def health_check():
        """Simple health check endpoint."""
        from config import validate_required_config

        missing = validate_required_config()
        status = "healthy" if not missing else "degraded"
        return jsonify({
            "status": status,
            "missing_config": missing,
        })

    # ── Start Cron Scheduler ──────────────────────────────────────
    _start_scheduler(app)

    logger.info("🚀 Mexico Limited AI Agent Backend started.")
    return app


def _start_scheduler(app: Flask) -> None:
    """Initializes the APScheduler for the payment watcher cron job."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from config import (
            PAYMENT_POLL_INTERVAL_MINUTES,
            NURTURE_POLL_INTERVAL_MINUTES,
        )

        scheduler = BackgroundScheduler()

        def run_payment_watcher():
            with app.app_context():
                from jobs.payment_watcher import check_approved_payments
                check_approved_payments()

        def run_nurture_watcher():
            with app.app_context():
                from jobs.nurture_watcher import run_nurture_cycle
                run_nurture_cycle()

        scheduler.add_job(
            run_payment_watcher,
            "interval",
            minutes=PAYMENT_POLL_INTERVAL_MINUTES,
            id="payment_watcher",
            name="Check for approved payments",
        )

        scheduler.add_job(
            run_nurture_watcher,
            "interval",
            minutes=NURTURE_POLL_INTERVAL_MINUTES,
            id="nurture_watcher",
            name="Follow up on cold leads",
        )

        scheduler.start()
        logger.info(
            f"📅 Payment watcher scheduled every "
            f"{PAYMENT_POLL_INTERVAL_MINUTES} minutes."
        )
        logger.info(
            f"📅 Nurture watcher scheduled every "
            f"{NURTURE_POLL_INTERVAL_MINUTES} minutes."
        )

    except ImportError:
        logger.warning(
            "apscheduler not installed. Payment watcher cron job disabled."
        )
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")


# ── Main ──────────────────────────────────────────────────────────

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
