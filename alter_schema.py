import os
import psycopg2

print("Connecting to the database...")
conn = psycopg2.connect(
    host=os.environ.get("DB_HOST", "hustaq-db.cj6cicg0wqlt.eu-west-1.rds.amazonaws.com"),
    database=os.environ.get("DB_NAME", "hustaq"),
    user=os.environ.get("DB_USER", "hustaq"),
    password=os.environ.get("DB_PASS", "hustaq_local"),
    port=int(os.environ.get("DB_PORT", 5432)),
    sslmode="require"
)
conn.autocommit = True
cur = conn.cursor()

alter_statements = """
ALTER TABLE sellers 
ADD COLUMN IF NOT EXISTS nomba_virtual_account VARCHAR(20),
ADD COLUMN IF NOT EXISTS nomba_bank_name VARCHAR(100),
ADD COLUMN IF NOT EXISTS nomba_bank_code VARCHAR(10);

ALTER TABLE orders 
ADD COLUMN IF NOT EXISTS nomba_reference VARCHAR(100);
"""

print("Applying ALTER TABLE schema updates...")
cur.execute(alter_statements)

print("Schema updated successfully!")
cur.close()
conn.close()
