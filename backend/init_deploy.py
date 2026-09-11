"""Inicialización idempotente para despliegue: esquema, roles, instrumentos y configuraciones."""
import os
from datetime import datetime, timedelta

from app import create_app
from app.extensions import db
from app.models import *  # registra todos los modelos
from app.models.usuario import Rol, Usuario
from app.models.instrumento import Instrumento, Dimension, Escala
from app.models.aplicacion import ConfiguracionAplicacion
from app.services.auth_service import AuthService

AREAS = ['Realista', 'Investigador', 'Artístico', 'Social', 'Emprendedor', 'Convencional']
ROLES = {
    'estudiante': 'Estudiante',
    'bienestar': 'Profesional de bienestar/orientación',
    'ti': 'Administrador técnico',
    'directivo': 'Directivo',
    'investigador': 'Investigador',
}

def get_or_create(model, defaults=None, **kwargs):
    obj = model.query.filter_by(**kwargs).first()
    if obj:
        return obj
    values = dict(kwargs)
    values.update(defaults or {})
    obj = model(**values)
    db.session.add(obj)
    db.session.flush()
    return obj

def ensure_instrument(nombre, dimension_name, desc, vmin, vmax):
    inst = get_or_create(Instrumento, nombre=nombre, defaults={
        'descripcion': desc, 'version': '2.0', 'activo': True
    })
    inst.activo = True
    dim = Dimension.query.filter_by(instrumento_id=inst.id, nombre=dimension_name).first()
    if not dim:
        dim = Dimension(instrumento_id=inst.id, nombre=dimension_name, descripcion=desc, peso=1.0, orden=1)
        db.session.add(dim); db.session.flush()
    for n, area in enumerate(AREAS, 1):
        esc = Escala.query.filter_by(dimension_id=dim.id, nombre=area).first()
        if not esc:
            esc = Escala(dimension_id=dim.id, nombre=area, descripcion=f'Área RIASEC {area}', orden=n)
            db.session.add(esc)
        esc.valor_minimo, esc.valor_maximo, esc.orden = vmin, vmax, n
    now = datetime.utcnow()
    cfg = ConfiguracionAplicacion.query.filter_by(instrumento_id=inst.id).first()
    if not cfg:
        cfg = ConfiguracionAplicacion(
            instrumento_id=inst.id, nombre=nombre, descripcion=desc,
            fecha_inicio=now - timedelta(days=1), fecha_fin=now + timedelta(days=3650),
            obligatoria=False, activa=True
        )
        db.session.add(cfg)
    else:
        cfg.activa = True
        if cfg.fecha_fin < now:
            cfg.fecha_fin = now + timedelta(days=3650)
    return inst

def main():
    app = create_app(os.getenv('FLASK_ENV', 'production'))
    with app.app_context():
        db.create_all()
        for nombre, desc in ROLES.items():
            get_or_create(Rol, nombre=nombre, defaults={'descripcion': desc, 'activo': True})
        ensure_instrument('Prueba de Intereses Vocacionales Holland', 'Intereses Vocacionales',
                          'Evaluación de intereses basada en RIASEC.', 0, 1)
        ensure_instrument('Prueba de Competencias Vocacionales Holland', 'Competencias Vocacionales',
                          'Evaluación de competencias basada en RIASEC.', 1, 4)
        admin_email = (os.getenv('ADMIN_EMAIL') or '').strip().lower()
        admin_password = os.getenv('ADMIN_PASSWORD') or ''
        if admin_email and admin_password and not Usuario.query.filter_by(email=admin_email).first():
            AuthService.validar_password(admin_password)
            rol = Rol.query.filter_by(nombre='ti').first()
            db.session.add(Usuario(email=admin_email, password_hash=AuthService.hash_password(admin_password),
                                   nombres='Administrador', apellidos='Sistema', rol_id=rol.id, activo=True))
        db.session.commit()
        print('OK: esquema, roles, instrumentos y configuraciones listos.')

if __name__ == '__main__':
    main()
