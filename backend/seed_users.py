import os
import secrets
"""
Script para crear usuarios de prueba en la base de datos.
Ejecutar con: python seed_users.py
"""

import bcrypt
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv('DATABASE_URL')
if not DB_URL:
    raise RuntimeError('Define DATABASE_URL antes de ejecutar este script.')


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')



DEMO_USER_PASSWORD = os.getenv('DEMO_USER_PASSWORD') or secrets.token_urlsafe(14) + 'Aa1!'
USERS = [
    # (email, password, nombres, apellidos, documento, tipo_doc, telefono, rol_nombre, programa_id, semestre, cohorte)
    ("admin@orientacion.edu.co",      DEMO_USER_PASSWORD,     "Carlos",   "Administrador", "1000000001", "CC", "3001111111", "ti",            None, None,  None),
    ("bienestar@orientacion.edu.co",   DEMO_USER_PASSWORD, "María",    "González",      "1000000002", "CC", "3002222222", "bienestar",     None, None,  None),
    ("directivo@orientacion.edu.co",   DEMO_USER_PASSWORD, "Roberto",  "Martínez",      "1000000003", "CC", "3003333333", "directivo",     None, None,  None),
    ("investigador@orientacion.edu.co","Investiga123*",  "Laura",    "Rodríguez",     "1000000004", "CC", "3004444444", "investigador",  None, None,  None),
    ("estudiante1@orientacion.edu.co", DEMO_USER_PASSWORD,"Juan",     "Pérez López",   "1000000005", "CC", "3005555555", "estudiante",    1,    5,     "2025-1"),
    ("estudiante2@orientacion.edu.co", DEMO_USER_PASSWORD,"Ana",      "García Ruiz",   "1000000006", "CC", "3006666666", "estudiante",    3,    3,     "2025-1"),
    ("estudiante3@orientacion.edu.co", DEMO_USER_PASSWORD,"Pedro",    "López Torres",  "1000000007", "CC", "3007777777", "estudiante",    5,    2,     "2025-2"),
]


def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Obtener mapa de roles
    cur.execute("SELECT id, nombre FROM roles")
    roles = {nombre: rid for rid, nombre in cur.fetchall()}
    print(f"Roles disponibles: {roles}")

    created = 0
    skipped = 0

    for email, pwd, nombres, apellidos, doc, tipo_doc, tel, rol_nombre, prog_id, semestre, cohorte in USERS:
        # Verificar si ya existe
        cur.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
        if cur.fetchone():
            print(f"  [SKIP] {email} ya existe")
            skipped += 1
            continue

        rol_id = roles.get(rol_nombre)
        if rol_id is None:
            print(f"  [ERROR] Rol '{rol_nombre}' no encontrado para {email}")
            continue

        pw_hash = hash_password(pwd)

        cur.execute("""
            INSERT INTO usuarios (email, password_hash, nombres, apellidos, documento,
                                  tipo_documento, telefono, rol_id, programa_id, semestre, cohorte, activo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
        """, (email, pw_hash, nombres, apellidos, doc, tipo_doc, tel, rol_id, prog_id, semestre, cohorte))

        print(f"  [OK] {email} ({rol_nombre})")
        created += 1

    conn.commit()
    cur.close()
    conn.close()

    print(f"\nResumen: {created} creados, {skipped} omitidos (ya existían)")
    print("\n========== USUARIOS DE PRUEBA ==========")
    print(f"{'Email':<42} {'Contraseña':<18} {'Rol'}")
    print("-" * 78)
    for email, pwd, _, _, _, _, _, rol, _, _, _ in USERS:
        print(f"{email:<42} {pwd:<18} {rol}")
    print("=" * 78)


if __name__ == "__main__":
    main()
