import os
import psycopg2

print("Connecting to the database...")
conn = psycopg2.connect(
    host=os.environ.get("DB_HOST", "hustaq-db.cj6cicg0wqlt.eu-west-1.rds.amazonaws.com"),
    database=os.environ.get("DB_NAME", "hustaq"),
    user=os.environ.get("DB_USER", "hustaq"),
    password=os.environ.get("DB_PASS", "hustaq_local"),
    port=int(os.environ.get("DB_PORT", 5432))
)
conn.autocommit = True
cur = conn.cursor()

print("Reading schema.sql...")
with open("src/db/schema.sql", "r") as f:
    sql = f.read()

print("Applying schema...")
cur.execute(sql)

print("Schema applied successfully!")
cur.close()
conn.close()
