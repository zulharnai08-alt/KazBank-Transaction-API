# KazBank — Step 6: Connection Pooling

This patch updates the existing Step 3–5 Flask project to use one shared psycopg3 `ConnectionPool`, adds `GET /health`, and provides a 20-request concurrency test.

## What Step 6 requires

1. Replace per-request `psycopg.connect()` calls with a shared `ConnectionPool`, created once at application startup.
2. Add `GET /health` returning pool statistics from `pool.get_stats()`.
3. Load-test the API with 20 concurrent requests and observe pool reuse.

For this Step 6, the pool is configured as `min_size=2`, `max_size=10`, `timeout=5.0`, matching the practice guide's example. Step 7 later specifies `max_size=8` for the final mini-project.

## Files in this patch

Copy these into the existing project root, preserving folders:

- `app/db.py` — replace the existing file. Existing route imports remain compatible because `get_conn()` now borrows a pooled connection.
- `app/__init__.py` — replace the existing file. It keeps the customers, accounts, transactions and transfers blueprints and adds `/health`.
- `test_pool.py` — copy to the project root.
- `requirements_step6.txt` — use it to add the dependency to your existing `requirements.txt`.

Do not replace `.env`, `run.py`, `schema_seed.py`, Step 1–5 route files, or your database.

## 1. Install the pool package

Activate the existing virtual environment, then run:

```powershell
pip install "psycopg-pool>=3.2,<4.0"
```

Also add this line to your existing `requirements.txt`:

```text
psycopg-pool>=3.2,<4.0
```

## 2. Start the application

Make sure PostgreSQL service is `Running`, then run:

```powershell
python run.py
```

Keep this terminal open. The pool is created once in `create_app()` at application startup. Each route continues to use `with get_conn() as conn:`; the helper now obtains a connection from the shared pool and returns it automatically when the context exits.

## 3. Task 2 — test GET /health

In a second VS Code terminal:

```powershell
Invoke-RestMethod "http://127.0.0.1:5000/health" | ConvertTo-Json -Depth 6
```

Expected response shape (exact statistic values will vary):

```json
{
  "status": "ok",
  "pool_stats": {
    "connections_num": 2,
    "requests_num": 1
  }
}
```

The real `pool_stats` dictionary may contain additional fields. The important evidence is that `/health` returns HTTP 200, `status: ok`, and the values returned by `pool.get_stats()`.

## 4. Task 3 — 20 concurrent requests

With Flask still running, open a second terminal and execute:

```powershell
python test_pool.py
```

The script sends 20 concurrent `GET /customers` requests using Python's `ThreadPoolExecutor`, then calls `/health` and prints the pool statistics.

Expected summary when the app and database are healthy:

```text
Concurrent requests: 20
Successful requests: 20
Failed requests: 0
PASS: all 20 concurrent requests completed using the shared pool.
```

The exact timing and pool counters vary between runs. Capture the output showing 20 requests and the statistics.

## Evidence for submission

1. Show `app/db.py` with `ConnectionPool(min_size=2, max_size=10)` and `init_pool()`.
2. Show the `GET /health` response containing `pool_stats`.
3. Show `python test_pool.py` with 20 concurrent requests and the final pool statistics.

The pool is shared by the routes. Do not create a new `ConnectionPool` inside a route handler.
