import psycopg2
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()
database_url = os.getenv('DATABASE_URL')
if not database_url:
    raise RuntimeError('Define DATABASE_URL antes de ejecutar este script.')
conn = psycopg2.connect(database_url)
cur = conn.cursor()
cur.execute("SELECT id, email, password_hash, activo FROM usuarios WHERE email = 'estudiante1@orientacion.edu.co'")
row = cur.fetchone()
if row:
    print(f"ID: {row[0]}, Email: {row[1]}, Activo: {row[3]}")
    print(f"Hash: {row[2][:40]}...")
    ok = bcrypt.checkpw(os.getenv("DEBUG_TEST_PASSWORD", "").encode("utf-8"), row[2].encode("utf-8"))
    print(f"Password check con bcrypt directo: {ok}")
else:
    print("Usuario NO encontrado")
cur.close()
conn.close()
