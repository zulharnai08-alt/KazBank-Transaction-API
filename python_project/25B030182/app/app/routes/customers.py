import psycopg
from flask import Blueprint, jsonify, request
from psycopg_pool import PoolTimeout

from app.db import get_conn

customers_bp = Blueprint("customers", __name__)


@customers_bp.route("/customers", methods=["GET"])
def list_customers():
    """GET /customers; optional filter: GET /customers?city=Almaty."""
    city = request.args.get("city", type=str)
    try:
        with get_conn() as conn:
            if city and city.strip():
                rows = conn.execute(
                    """
                    SELECT customer_id, full_name, city, email
                    FROM customers
                    WHERE city = %s
                    ORDER BY customer_id
                    """,
                    (city.strip(),),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT customer_id, full_name, city, email
                    FROM customers
                    ORDER BY customer_id
                    """
                ).fetchall()
        return jsonify([
            {"customer_id": r[0], "full_name": r[1], "city": r[2], "email": r[3]}
            for r in rows
        ]), 200
    except (psycopg.OperationalError, PoolTimeout):
        return jsonify({"error": "Database unavailable"}), 503


@customers_bp.route("/customers", methods=["POST"])
def create_customer():
    """Create a customer with explicit COMMIT/ROLLBACK and PostgreSQL error mapping."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object"}), 400

    full_name = data.get("full_name")
    email = data.get("email")
    city = data.get("city", "Almaty")

    # Reject invalid types/blank strings. Missing required values are sent as None
    # so PostgreSQL's NOT NULL constraint is also handled below.
    if full_name is not None and (not isinstance(full_name, str) or not full_name.strip()):
        return jsonify({"error": "full_name must be a non-empty string"}), 400
    if email is not None and (not isinstance(email, str) or not email.strip()):
        return jsonify({"error": "email must be a non-empty string"}), 400
    if not isinstance(city, str) or not city.strip():
        return jsonify({"error": "city must be a non-empty string"}), 400

    try:
        with get_conn() as conn:
            try:
                row = conn.execute(
                    """
                    INSERT INTO customers (full_name, city, email)
                    VALUES (%s, %s, %s)
                    RETURNING customer_id, full_name, city, email
                    """,
                    (
                        full_name.strip() if isinstance(full_name, str) else None,
                        city.strip(),
                        email.strip() if isinstance(email, str) else None,
                    ),
                ).fetchone()
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        return jsonify({
            "customer_id": row[0],
            "full_name": row[1],
            "city": row[2],
            "email": row[3],
        }), 201
    except psycopg.errors.UniqueViolation:
        return jsonify({"error": "Email already registered"}), 409
    except psycopg.errors.NotNullViolation as exc:
        column = getattr(getattr(exc, "diag", None), "column_name", None)
        return jsonify({"error": "Missing required field", "field": column}), 400
    except (psycopg.OperationalError, PoolTimeout):
        return jsonify({"error": "Database unavailable"}), 503


@customers_bp.route("/customers/<int:customer_id>", methods=["PUT"])
def update_customer(customer_id: int):
    """Optional CRUD endpoint retained from Step 3."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object"}), 400

    try:
        with get_conn() as conn:
            try:
                current = conn.execute(
                    "SELECT full_name, city, email FROM customers WHERE customer_id = %s",
                    (customer_id,),
                ).fetchone()
                if current is None:
                    conn.rollback()
                    return jsonify({"error": "Customer not found"}), 404

                full_name = data.get("full_name", current[0])
                city = data.get("city", current[1])
                email = data.get("email", current[2])
                if not all(isinstance(v, str) and v.strip() for v in (full_name, city, email)):
                    conn.rollback()
                    return jsonify({"error": "full_name, city and email must be non-empty strings"}), 400

                conn.execute(
                    """UPDATE customers SET full_name = %s, city = %s, email = %s
                       WHERE customer_id = %s""",
                    (full_name.strip(), city.strip(), email.strip(), customer_id),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return jsonify({"updated": customer_id}), 200
    except psycopg.errors.UniqueViolation:
        return jsonify({"error": "Email already registered"}), 409
    except psycopg.errors.NotNullViolation:
        return jsonify({"error": "Missing required field"}), 400
    except (psycopg.OperationalError, PoolTimeout):
        return jsonify({"error": "Database unavailable"}), 503


@customers_bp.route("/customers/<int:customer_id>", methods=["DELETE"])
def delete_customer(customer_id: int):
    """Optional CRUD endpoint retained from Step 3."""
    try:
        with get_conn() as conn:
            try:
                cur = conn.execute(
                    "DELETE FROM customers WHERE customer_id = %s",
                    (customer_id,),
                )
                if cur.rowcount == 0:
                    conn.rollback()
                    return jsonify({"error": "Customer not found"}), 404
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return jsonify({"deleted": customer_id}), 200
    except psycopg.errors.ForeignKeyViolation:
        return jsonify({"error": "Cannot delete customer with existing accounts"}), 409
    except (psycopg.OperationalError, PoolTimeout):
        return jsonify({"error": "Database unavailable"}), 503
