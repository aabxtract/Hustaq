import psycopg2
import os

print("Connecting to the database...")
conn = psycopg2.connect(
    host="hustaq-db.cj6cicg0wqlt.eu-west-1.rds.amazonaws.com",
    database="hustaq",
    user="hustaq",
    password="hustaq_prod_123_changeme",
    port=5432
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
