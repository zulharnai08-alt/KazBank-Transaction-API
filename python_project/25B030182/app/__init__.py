from flask import Flask, jsonify
from psycopg import OperationalError
from psycopg_pool import PoolTimeout

from app.db import get_pool, init_pool
from app.routes.accounts import accounts_bp
from app.routes.customers import customers_bp
from app.routes.transactions import transactions_bp
from app.routes.transfers import transfers_bp


def create_app() -> Flask:
    app = Flask(__name__)

    # Step 7: create one shared pool at application startup (min=2, max=8).
    init_pool()

    app.register_blueprint(customers_bp)
    app.register_blueprint(accounts_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(transfers_bp)

    @app.route("/health", methods=["GET"])
    def health():
        pool = get_pool()
        try:
            with pool.connection(timeout=5.0) as conn:
                conn.execute("SELECT 1")
            return jsonify({"status": "ok", "pool_stats": pool.get_stats()}), 200
        except (OperationalError, PoolTimeout):
            return jsonify({
                "status": "error",
                "error": "Database unavailable",
                "pool_stats": pool.get_stats(),
            }), 503

    return app
