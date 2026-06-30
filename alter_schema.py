import psycopg2

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
