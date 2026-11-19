# KazBank Transaction API — Step 7

This is the final mini-project package for the existing KazBank schema from Step 2. It uses the tables and columns already created by `schema_seed.py`:

- `customers(customer_id, full_name, city, email)`
- `accounts(account_id, customer_id, account_number, balance)`
- `transactions(transaction_id, account_id, amount, tx_type, created_at)`

## Requirements from the practice guide

1. Schema: `customers`, `accounts`, `transactions`.
2. Main endpoints:
   - `GET /customers`
   - `POST /customers`
   - `GET /accounts?customer_id=n`
   - `POST /transfer`
   - `GET /transactions?account_id=n`
3. Shared `ConnectionPool(min_size=2, max_size=8)`.
4. Every write endpoint explicitly uses `commit()` / `rollback()`.
5. `/transfer` uses `SERIALIZABLE` and retries `SerializationFailure` (SQLSTATE 40001).
6. Structured JSON and correct HTTP status codes.
7. `UniqueViolation` -> 409, `NotNullViolation` -> 400, `OperationalError`/pool timeout -> 503.
8. SQL values are passed using `%s` parameters.
9. `GET /health` returns `pool.get_stats()` (required by rubric R8).

The package also retains `PUT /customers/<id>`, `DELETE /customers/<id>`, and `POST /transactions` from earlier practice steps.

## Install / integrate

1. Stop Flask with `Ctrl+C`.
2. Back up the existing `app` folder.
3. Copy this package's `app` folder into the project, replacing the existing `app` folder. This package consolidates the final route implementations from Steps 3–6.
4. Copy `run.py` to the project root (or update the existing one so `use_reloader=False`). Do not replace your `.env`, `schema_seed.py`, or `test_connection.py`.
5. In the activated virtual environment run:

```powershell
pip install -r requirements_step7.txt
```

If you prefer to keep the existing `requirements.txt`, add this line to it:

```text
psycopg-pool>=3.2,<4.0
```

6. Ensure PostgreSQL is running and your existing `.env` contains the correct `DATABASE_URL`. Then start:

```powershell
python run.py
```

The final-project pool is `min_size=2, max_size=8` (Step 6 used max_size=10; Step 7 explicitly changes it to 8).

## Test endpoints (PowerShell)

Keep the Flask terminal open. Run these in a second terminal.

### 1. GET all customers

```powershell
Invoke-RestMethod "http://127.0.0.1:5000/customers" | ConvertTo-Json -Depth 5
```

### 2. POST a new customer

```powershell
$body = @{
    full_name = "Final Project Test"
    city = "Almaty"
    email = "final-project-test@example.com"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:5000/customers" -Method POST -ContentType "application/json" -Body $body
```

This creates one test row. Use a different email if it already exists.

### 3. GET accounts for a customer

```powershell
Invoke-RestMethod "http://127.0.0.1:5000/accounts?customer_id=1" | ConvertTo-Json -Depth 5
```

### 4. POST a transfer

```powershell
$body = @{
    from_account_id = 1
    to_account_id = 2
    amount = 1000
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:5000/transfer" -Method POST -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 5
```

A successful response includes balances, `isolation_level: SERIALIZABLE`, deterministic `lock_order`, and `retry_attempts`. A transfer writes a debit row and a credit row in `transactions` and commits both balance updates together.

### 5. GET transaction history

```powershell
Invoke-RestMethod "http://127.0.0.1:5000/transactions?account_id=1" | ConvertTo-Json -Depth 5
```

### 6. GET pool health / stats

```powershell
Invoke-RestMethod "http://127.0.0.1:5000/health" | ConvertTo-Json -Depth 6
```

Expect `status: ok` and a `pool_stats` object returned by `pool.get_stats()`.

## Error-path checks

### Duplicate email -> HTTP 409

Use an email already in the database, for example `arman@example.com`:

```powershell
$body = @{ full_name="Duplicate"; city="Almaty"; email="arman@example.com" } | ConvertTo-Json
try {
    Invoke-RestMethod -Uri "http://127.0.0.1:5000/customers" -Method POST -ContentType "application/json" -Body $body
} catch { "HTTP Status: $([int]$_.Exception.Response.StatusCode)"; $_.ErrorDetails.Message }
```

### Missing `full_name` -> HTTP 400

```powershell
$body = @{ city="Almaty"; email="missing-name-final@example.com" } | ConvertTo-Json
try {
    Invoke-RestMethod -Uri "http://127.0.0.1:5000/customers" -Method POST -ContentType "application/json" -Body $body
} catch { "HTTP Status: $([int]$_.Exception.Response.StatusCode)"; $_.ErrorDetails.Message }
```

### SQL injection check

```powershell
Invoke-RestMethod "http://127.0.0.1:5000/customers?city=Almaty%27%20OR%20%271%27%3D%271" | ConvertTo-Json
```

The malicious input is treated as a literal city value; it must not return all customers.

## Submission

Keep your earlier `schema_seed.py` in the root and run it if you need to create/seed the tables from Python. Do not commit `.env` or your PostgreSQL password. Include the project in the course GitLab repository under:

```text
python_project/<your_id>/
```

Include a README with setup instructions and sample PowerShell/curl commands.
