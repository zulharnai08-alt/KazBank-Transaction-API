import psycopg
from flask import Blueprint, jsonify, request
from psycopg_pool import PoolTimeout

from app.db import get_conn

accounts_bp = Blueprint("accounts", __name__)


@accounts_bp.route("/accounts", methods=["GET"])
def list_accounts():
    """GET /accounts?customer_id=n."""
    customer_id = request.args.get("customer_id", type=int)
    if customer_id is None or customer_id <= 0:
        return jsonify({"error": "Provide a positive customer_id query parameter"}), 400

    try:
        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT account_id, customer_id, account_number, balance
                FROM accounts
                WHERE customer_id = %s
                ORDER BY account_id
                """,
                (customer_id,),
            ).fetchall()
        return jsonify([
            {
                "account_id": r[0],
                "customer_id": r[1],
                "account_number": r[2],
                "balance": str(r[3]),
            }
            for r in rows
        ]), 200
    except (psycopg.OperationalError, PoolTimeout):
        return jsonify({"error": "Database unavailable"}), 503
