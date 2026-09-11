"""Check existing tables and drop them, then run init_db.sql."""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
database_url = os.getenv('DATABASE_URL')
if not database_url:
    raise RuntimeError('Define DATABASE_URL antes de ejecutar este script.')
conn = psycopg2.connect(database_url)
conn.autocommit = True
cur = conn.cursor()

# List existing tables
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
tables = [r[0] for r in cur.fetchall()]
print(f"Tablas existentes ({len(tables)}):")
for t in tables:
    print(f"  - {t}")

# Drop all existing tables (CASCADE)
print("\n--- Eliminando tablas existentes ---")
for t in tables:
    try:
        cur.execute(f'DROP TABLE IF EXISTS "{t}" CASCADE')
        print(f"  Eliminada: {t}")
    except Exception as e:
        print(f"  Error con {t}: {e}")

# Run init_db.sql
print("\n--- Ejecutando init_db.sql ---")
with open('sql/init_db.sql', 'r', encoding='utf-8') as f:
    sql = f.read()

cur.execute(sql)
print("init_db.sql ejecutado exitosamente!")

# Verify
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
new_tables = [r[0] for r in cur.fetchall()]
print(f"\nNuevas tablas ({len(new_tables)}):")
for t in new_tables:
    print(f"  - {t}")

conn.close()
print("\n¡Base de datos configurada correctamente!")
