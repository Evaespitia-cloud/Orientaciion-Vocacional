import sys
sys.path.insert(0, 'c:/Users/ASUS/Desktop/ORIENTACION V/backend')
from app import create_app
from app.extensions import db
from app.models.usuario import Usuario
from app.models.aplicacion import Aplicacion
from app.models.resultado import PerfilVocacional, ResultadoDimension

app = create_app()

EMAILS = [
    'laura.torres@orientacion.edu.co',
    'carlos.mendez@orientacion.edu.co',
    'sofia.guerrero@orientacion.edu.co',
    'andres.castillo@orientacion.edu.co',
    'valentina.rios@orientacion.edu.co',
    'miguel.herrera@orientacion.edu.co',
    'isabella.rojas@orientacion.edu.co',
    'daniel.florez@orientacion.edu.co',
    'camila.jimenez@orientacion.edu.co',
    'juan.morales@orientacion.edu.co',
]

with app.app_context():
    print("Iniciando limpieza de datos de estudiantes simulados...")
    for email in EMAILS:
        u = Usuario.query.filter_by(email=email).first()
        if u:
            print(f"Limpiando aplicaciones para {email} (ID={u.id})...")
            # Delete apps
            apps = Aplicacion.query.filter_by(usuario_id=u.id).all()
            for ap in apps:
                # cascade should delete profiles and dimensions, but let's delete explicitly to be safe
                PerfilVocacional.query.filter_by(aplicacion_id=ap.id).delete()
                ResultadoDimension.query.filter_by(aplicacion_id=ap.id).delete()
                db.session.delete(ap)
            print(f"  [OK] Eliminadas {len(apps)} aplicaciones.")
    db.session.commit()
    print("Limpieza completada.")
