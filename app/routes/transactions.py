from decimal import Decimal, InvalidOperation

import psycopg
from flask import Blueprint, jsonify, request
from psycopg_pool import PoolTimeout

from app.db import get_conn

transactions_bp = Blueprint("transactions", __name__)


@transactions_bp.route("/transactions", methods=["GET"])
def list_transactions():
    """GET /transactions?account_id=n."""
    account_id = request.args.get("account_id", type=int)
    if account_id is None or account_id <= 0:
        return jsonify({"error": "Provide a positive account_id query parameter"}), 400

    try:
        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT transaction_id, account_id, amount, tx_type, created_at
                FROM transactions
                WHERE account_id = %s
                ORDER BY transaction_id
                """,
                (account_id,),
            ).fetchall()
        return jsonify([
            {
                "transaction_id": r[0],
                "account_id": r[1],
                "amount": str(r[2]),
                "tx_type": r[3],
                "created_at": r[4].isoformat() if r[4] else None,
            }
            for r in rows
        ]), 200
    except (psycopg.OperationalError, PoolTimeout):
        return jsonify({"error": "Database unavailable"}), 503


# POST /transactions is retained from Step 3 for backward compatibility.
@transactions_bp.route("/transactions", methods=["POST"])
def create_transaction():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object"}), 400

    account_id = data.get("account_id")
    tx_type = data.get("tx_type")
    if isinstance(account_id, bool) or not isinstance(account_id, int) or account_id <= 0:
        return jsonify({"error": "account_id must be a positive integer"}), 400
    if not isinstance(tx_type, str) or tx_type.lower().strip() not in ("debit", "credit"):
        return jsonify({"error": "tx_type must be debit or credit"}), 400
    tx_type = tx_type.lower().strip()

    try:
        amount = Decimal(str(data.get("amount", "")))
        if not amount.is_finite() or amount <= 0 or amount.quantize(Decimal("0.01")) != amount:
            raise InvalidOperation
        amount = amount.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return jsonify({"error": "amount must be a positive number with at most 2 decimal places"}), 400

    try:
        with get_conn() as conn:
            try:
                row = conn.execute(
                    "SELECT balance FROM accounts WHERE account_id = %s FOR UPDATE",
                    (account_id,),
                ).fetchone()
                if row is None:
                    conn.rollback()
                    return jsonify({"error": "Account not found"}), 404

                balance = row[0]
                if tx_type == "debit" and balance < amount:
                    conn.rollback()
                    return jsonify({"error": "Insufficient funds", "balance": str(balance)}), 400

                operator = "-" if tx_type == "debit" else "+"
                updated = conn.execute(
                    f"UPDATE accounts SET balance = balance {operator} %s WHERE account_id = %s RETURNING balance",
                    (amount, account_id),
                ).fetchone()[0]
                tx = conn.execute(
                    """INSERT INTO transactions (account_id, amount, tx_type)
                       VALUES (%s, %s, %s) RETURNING transaction_id""",
                    (account_id, amount, tx_type),
                ).fetchone()[0]
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        return jsonify({
            "transaction_id": tx,
            "account_id": account_id,
            "amount": str(amount),
            "tx_type": tx_type,
            "balance": str(updated),
        }), 201
    except psycopg.errors.NotNullViolation:
        return jsonify({"error": "Missing required field"}), 400
    except (psycopg.OperationalError, PoolTimeout):
        return jsonify({"error": "Database unavailable"}), 503
