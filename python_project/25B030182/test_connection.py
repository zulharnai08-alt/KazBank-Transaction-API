import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

conn_str = os.getenv("DATABASE_URL")
print("DATABASE_URL loaded:", bool(conn_str))

with psycopg.connect(conn_str) as conn:
    print("Autocommit:", conn.autocommit)

    with conn.cursor() as cur:
        cur.execute("SELECT version()")
        row = cur.fetchone()
        print("PostgreSQL version:")
        print(row[0])