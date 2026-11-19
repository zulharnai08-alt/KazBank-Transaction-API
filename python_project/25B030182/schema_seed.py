
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
conn_str = os.getenv("DATABASE_URL")

# создание бд

SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS customers (
        customer_id SERIAL PRIMARY KEY,
        full_name TEXT NOT NULL,
        city TEXT DEFAULT 'Almaty',
        email TEXT UNIQUE NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS accounts (
        account_id SERIAL PRIMARY KEY,
        customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
        account_number VARCHAR(30) NOT NULL UNIQUE,
        balance NUMERIC(15,2) NOT NULL DEFAULT 0
            CHECK (balance >= 0)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(account_id),
        amount NUMERIC(15,2) NOT NULL CHECK (amount > 0),
        tx_type VARCHAR(10) NOT NULL
            CHECK (tx_type IN ('debit', 'credit')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
]

# 10 кастомеров
CUSTOMERS = [
    ("Arman Bekov", "Almaty", "arman@example.com"),
    ("Zarina Seiit", "Astana", "zarina@example.com"),
    ("Daniyar Nurlan", "Shymkent", "daniyar@example.com"),
    ("Aigerim Sadyk", "Almaty", "aigerim@example.com"),
    ("Timur Askar", "Aktobe", "timur@example.com"),
    ("Madina Omar", "Astana", "madina@example.com"),
    ("Nursultan Ali", "Almaty", "nursultan@example.com"),
    ("Aruzhan Bek", "Taraz", "aruzhan@example.com"),
    ("Dias Karim", "Aktau", "dias@example.com"),
    ("Sabina Ermek", "Almaty", "sabina@example.com")
]

# 15 акков с емаилом
ACCOUNT_DATA = [
    ("arman@example.com", "KZ1000000001", 150000),
    ("arman@example.com", "KZ1000000002", 200000),
    ("zarina@example.com", "KZ1000000003", 100000),
    ("zarina@example.com", "KZ1000000004", 250000),
    ("daniyar@example.com", "KZ1000000005", 175000),
    ("daniyar@example.com", "KZ1000000006", 90000),
    ("aigerim@example.com", "KZ1000000007", 300000),
    ("aigerim@example.com", "KZ1000000008", 125000),
    ("timur@example.com", "KZ1000000009", 50000),
    ("timur@example.com", "KZ1000000010", 220000),
    ("madina@example.com", "KZ1000000011", 180000),
    ("nursultan@example.com", "KZ1000000012", 75000),
    ("aruzhan@example.com", "KZ1000000013", 400000),
    ("dias@example.com", "KZ1000000014", 95000),
    ("sabina@example.com", "KZ1000000015", 160000)
]

with psycopg.connect(conn_str) as conn:

    # создать все 3 таблитцы
    for statement in SCHEMA:
        conn.execute(statement)

    # добавить 10 к нему
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO customers (full_name, city, email)
            VALUES (%s, %s, %s)
            ON CONFLICT (email) DO NOTHING
            """,
            CUSTOMERS
        )

    # получить кастомизацию
    rows = conn.execute(
        "SELECT customer_id, email FROM customers"
    ).fetchall()

    customer_ids = {
        email: customer_id
        for customer_id, email in rows
    }

    accounts = [
        (customer_ids[email], number, balance)
        for email, number, balance in ACCOUNT_DATA
    ]

    # добавление 15 акков
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO accounts (customer_id, account_number, balance)
            VALUES (%s, %s, %s)
            ON CONFLICT (account_number) DO NOTHING
            """,
            accounts
        )

    conn.commit()

    # 4. верификация уникальных констант
    conn.execute("SAVEPOINT duplicate_test")

    try:
        conn.execute(
            """
            INSERT INTO accounts
            (customer_id, account_number, balance)
            VALUES (%s, %s, %s)
            """,
            (
                customer_ids["arman@example.com"],
                "KZ1000000001",
                50000
            )
        )

        conn.execute("ROLLBACK TO SAVEPOINT duplicate_test")
        print("FAIL: Duplicate account was accepted!")

    except psycopg.errors.UniqueViolation:
        conn.execute("ROLLBACK TO SAVEPOINT duplicate_test")
        print("PASS: Duplicate account rejected by UNIQUE!")

    conn.execute("RELEASE SAVEPOINT duplicate_test")
    conn.commit()

    # 5. верификация дат
    customer_count = conn.execute(
        "SELECT COUNT(*) FROM customers"
    ).fetchone()[0]

    account_count = conn.execute(
        "SELECT COUNT(*) FROM accounts"
    ).fetchone()[0]

    transaction_table = conn.execute(
        "SELECT COUNT(*) FROM transactions"
    ).fetchone()[0]

    print("\n===== KAZBANK DATABASE REPORT =====")
    print("Customers:", customer_count)
    print("Accounts:", account_count)
    print("Transactions:", transaction_table)
    print("Database schema created successfully!")
