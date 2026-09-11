import sys; sys.path.insert(0, 'backend')
from app import create_app
from sqlalchemy import text
app = create_app()
with app.app_context():
    from app.extensions import db
    # Ver tabla grados
    rows = db.session.execute(text('SELECT id, nombre FROM grados ORDER BY id')).fetchall()
    print('=== GRADOS TABLE ===')
    for r in rows: print(f'  id={r[0]}  nombre={r[1]}')
    # Ver distribucion de grado_id en usuarios estudiante
    rows2 = db.session.execute(text("SELECT u.grado_id, g.nombre, COUNT(*) as cnt FROM usuarios u LEFT JOIN grados g ON u.grado_id=g.id WHERE u.rol_id=(SELECT id FROM roles WHERE nombre='estudiante') GROUP BY u.grado_id, g.nombre ORDER BY cnt DESC")).fetchall()
    print('=== GRADO_ID DISTRIBUTION (estudiantes) ===')
    for r in rows2: print(f'  grado_id={r[0]}  nombre={r[1]}  count={r[2]}')
    # Ver valores en datos_demograficos para grado_escolar
    rows3 = db.session.execute(text("SELECT d.valor, COUNT(*) as cnt FROM datos_demograficos d JOIN campos_demograficos c ON d.campo_id=c.id WHERE c.nombre='grado_escolar' GROUP BY d.valor ORDER BY cnt DESC")).fetchall()
    print('=== DATOS_DEMOGRAFICOS grado_escolar VALUES ===')
    for r in rows3: print(f'  valor={r[0]}  count={r[1]}')
