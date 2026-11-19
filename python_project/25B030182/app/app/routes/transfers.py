import time
from decimal import Decimal, InvalidOperation

import psycopg
from flask import Blueprint, jsonify, request
from psycopg import IsolationLevel
from psycopg_pool import PoolTimeout

from app.db import get_conn

transfers_bp = Blueprint("transfers", __name__)


def _positive_id(value, field):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _positive_amount(value):
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount <= 0:
            raise InvalidOperation
        normalized = amount.quantize(Decimal("0.01"))
        if normalized != amount:
            raise ValueError("amount must have at most 2 decimal places")
        return normalized
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("amount must be a positive number with at most 2 decimal places")


def _transfer_once(from_id: int, to_id: int, amount: Decimal):
    """Run one SERIALIZABLE transfer attempt on one pooled connection."""
    with get_conn() as conn:
        # Must be set before the first SQL statement in this transaction.
        conn.isolation_level = IsolationLevel.SERIALIZABLE

        balances = {}
        # Deterministic lock acquisition prevents opposite-order deadlocks.
        for account_id in sorted((from_id, to_id)):
            row = conn.execute(
                """SELECT account_id, balance FROM accounts
                   WHERE account_id = %s FOR UPDATE""",
                (account_id,),
            ).fetchone()
            if row is None:
                conn.rollback()
                return ({"error": "Account not found", "account_id": account_id}, 404)
            balances[row[0]] = row[1]

        if balances[from_id] < amount:
            conn.rollback()
            return ({
                "error": "Insufficient funds",
                "available_balance": str(balances[from_id]),
            }, 400)

        # Savepoint contains both balance changes and both transaction records.
        conn.execute("SAVEPOINT transfer_changes")
        try:
            debit = conn.execute(
                """UPDATE accounts SET balance = balance - %s
                   WHERE account_id = %s AND balance >= %s
                   RETURNING balance""",
                (amount, from_id, amount),
            ).fetchone()
            if debit is None:
                conn.execute("ROLLBACK TO SAVEPOINT transfer_changes")
                conn.execute("RELEASE SAVEPOINT transfer_changes")
                conn.rollback()
                return ({"error": "Insufficient funds; transfer cancelled"}, 400)

            conn.execute(
                """INSERT INTO transactions (account_id, amount, tx_type)
                   VALUES (%s, %s, 'debit')""",
                (from_id, amount),
            )

            credit = conn.execute(
                """UPDATE accounts SET balance = balance + %s
                   WHERE account_id = %s RETURNING balance""",
                (amount, to_id),
            ).fetchone()
            if credit is None:
                conn.execute("ROLLBACK TO SAVEPOINT transfer_changes")
                conn.execute("RELEASE SAVEPOINT transfer_changes")
                conn.rollback()
                return ({"error": "Destination account not found; transfer cancelled"}, 404)

            conn.execute(
                """INSERT INTO transactions (account_id, amount, tx_type)
                   VALUES (%s, %s, 'credit')""",
                (to_id, amount),
            )
        except psycopg.IntegrityError as exc:
            conn.execute("ROLLBACK TO SAVEPOINT transfer_changes")
            conn.execute("RELEASE SAVEPOINT transfer_changes")
            conn.rollback()
            return ({
                "error": "Transfer constraint violation; all transfer changes rolled back",
                "database_error": type(exc).__name__,
            }, 400)

        conn.execute("RELEASE SAVEPOINT transfer_changes")
        conn.commit()
        return ({
            "status": "success",
            "from_account_id": from_id,
            "to_account_id": to_id,
            "amount": str(amount),
            "from_balance": str(debit[0]),
            "to_balance": str(credit[0]),
            "isolation_level": "SERIALIZABLE",
            "lock_order": sorted((from_id, to_id)),
        }, 201)


def _with_serialization_retry(operation, max_retries=3):
    """Retry the complete transaction on PostgreSQL SQLSTATE 40001."""
    for attempt in range(1, max_retries + 1):
        try:
            return operation(), attempt
        except psycopg.errors.SerializationFailure:
            if attempt == max_retries:
                raise
            time.sleep(0.05 * attempt)
    raise RuntimeError("Maximum serialization retries exceeded")


@transfers_bp.route("/transfer", methods=["POST"])
def transfer_money():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object"}), 400

    try:
        from_id = _positive_id(data.get("from_account_id"), "from_account_id")
        to_id = _positive_id(data.get("to_account_id"), "to_account_id")
        amount = _positive_amount(data.get("amount"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if from_id == to_id:
        return jsonify({"error": "Source and destination accounts must be different"}), 400

    try:
        (payload, status), attempts = _with_serialization_retry(
            lambda: _transfer_once(from_id, to_id, amount),
            max_retries=3,
        )
        payload["retry_attempts"] = attempts
        return jsonify(payload), status
    except psycopg.errors.SerializationFailure:
        return jsonify({
            "error": "Serialization conflict after retries; please retry the request",
            "sqlstate": "40001",
            "retry_attempts": 3,
        }), 409
    except (psycopg.OperationalError, PoolTimeout):
        return jsonify({"error": "Database unavailable"}), 503
