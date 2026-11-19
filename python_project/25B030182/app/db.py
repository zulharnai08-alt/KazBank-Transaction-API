"""One shared psycopg3 ConnectionPool for the KazBank API."""

import os
from threading import Lock

from dotenv import load_dotenv
from psycopg_pool import ConnectionPool

load_dotenv()

_pool: ConnectionPool | None = None
_pool_lock = Lock()


def init_pool() -> ConnectionPool:
    """Create the application pool once; final-project size is min=2, max=8."""
    global _pool

    if _pool is not None:
        return _pool

    with _pool_lock:
        if _pool is None:
            conninfo = os.getenv("DATABASE_URL")
            if not conninfo:
                raise RuntimeError(
                    "DATABASE_URL не найден. Проверь файл .env в корне проекта."
                )

            _pool = ConnectionPool(
                conninfo=conninfo,
                min_size=2,
                max_size=8,
                timeout=5.0,
                open=False,
                name="kazbank-final-pool",
            )
            # Open asynchronously: the Flask app can still answer 503 if DB goes down.
            _pool.open()

    return _pool


def get_pool() -> ConnectionPool:
    return init_pool()


def get_conn():
    """Borrow a pooled connection; the context manager returns it automatically."""
    return get_pool().connection(timeout=5.0)


def close_pool() -> None:
    """Close the pool during tests or graceful shutdown."""
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.close()
            _pool = None
