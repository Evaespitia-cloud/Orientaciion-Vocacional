"""Script to update school type options in DB."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('backend/.env')
database_url = os.getenv('DATABASE_URL')
if not database_url:
    raise RuntimeError('Define DATABASE_URL antes de ejecutar este script.')
conn = psycopg2.connect(database_url)
conn.autocommit = True
cur = conn.cursor()

nuevas_opciones = '["Público", "Privado", "Semi-privado", "Militar"]'
cur.execute(
    "UPDATE campos_demograficos SET opciones = %s::json WHERE nombre = 'tipo_colegio'",
    (nuevas_opciones,)
)
print(f'Actualizado: {cur.rowcount} registro(s)')

cur.execute("SELECT nombre, opciones FROM campos_demograficos WHERE nombre='tipo_colegio'")
print(cur.fetchone())
conn.close()
