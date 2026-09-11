"""Eliminar campos demográficos duplicados (IDs 1-6, los datos están en IDs 7-12)."""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv('backend/.env')
database_url = os.getenv('DATABASE_URL')
if not database_url:
    raise RuntimeError('Define DATABASE_URL antes de ejecutar este script.')
conn = psycopg2.connect(database_url)
conn.autocommit = True
cur = conn.cursor()

# Verificar que IDs 1-6 no tienen datos antes de eliminar
cur.execute("SELECT COUNT(*) FROM datos_demograficos WHERE campo_id BETWEEN 1 AND 6")
count = cur.fetchone()[0]
print(f"Datos vinculados a campos 1-6: {count}")

if count == 0:
    cur.execute("DELETE FROM campos_demograficos WHERE id BETWEEN 1 AND 6")
    print(f"Eliminados: {cur.rowcount} campos duplicados")
else:
    # Reasignar datos al segundo set y eliminar duplicados
    print("Hay datos en IDs 1-6, reasignando a IDs 7-12...")
    cur.execute("""
        UPDATE datos_demograficos dd
        SET campo_id = (
            SELECT cd2.id FROM campos_demograficos cd2
            WHERE cd2.nombre = (
                SELECT cd1.nombre FROM campos_demograficos cd1 WHERE cd1.id = dd.campo_id
            )
            AND cd2.id > 6 LIMIT 1
        )
        WHERE campo_id BETWEEN 1 AND 6
    """)
    print(f"Reasignados: {cur.rowcount}")
    cur.execute("DELETE FROM campos_demograficos WHERE id BETWEEN 1 AND 6")
    print(f"Eliminados: {cur.rowcount} campos duplicados")

print("\n=== Campos restantes ===")
cur.execute("SELECT id, nombre, obligatorio, orden FROM campos_demograficos ORDER BY orden")
for row in cur.fetchall():
    print(row)

print("\n=== Datos demográficos ===")
cur.execute("""
    SELECT u.email, cd.nombre, dd.valor
    FROM datos_demograficos dd
    JOIN campos_demograficos cd ON cd.id = dd.campo_id
    JOIN usuarios u ON u.id = dd.usuario_id
    ORDER BY u.email, cd.orden
""")
for row in cur.fetchall():
    print(row)

conn.close()
