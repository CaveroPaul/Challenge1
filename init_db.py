from pathlib import Path
import psycopg2

DB = dict(host="localhost", port=5432, dbname="ecomerce", user="postgres", password="admin")
SQL_FILE = Path(__file__).parent / "init_db.sql"

sql = SQL_FILE.read_text(encoding="utf-8")

with psycopg2.connect(**DB) as conn:
    with conn.cursor() as cur:
        cur.execute(sql)

print("init_db.sql executed successfully.")
