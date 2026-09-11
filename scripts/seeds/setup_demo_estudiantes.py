"""
Prepara los estados de aplicaciones para la sustentación:
- María Fernanda (ID=8): Intereses=completada, Competencias=completada, Seguimiento=sin iniciar
- Otros: variedad de estados
"""
import sys, random
from datetime import datetime, timedelta
sys.path.insert(0, 'backend')
from backend.app import create_app
from backend.app.extensions import db
from backend.app.models.aplicacion import Aplicacion, ConfiguracionAplicacion
from backend.app.models.resultado import PerfilVocacional, ResultadoDimension
from backend.app.models.instrumento import Dimension

app = create_app()

# IDs de configs disponibles
CFG_INTERESES    = 1   # Prueba de Intereses (obligatoria)
CFG_COMPETENCIAS = 2   # Prueba de Competencias (obligatoria)
CFG_SEGUIMIENTO  = 14  # Evaluación Periodo III (seguimiento)

MARIA_FERNANDA_ID = 8

# Perfil base de María Fernanda (basado en sus apps existentes: Investigador)
PERFIL_MF = {
    'perfil_principal': 'Investigador',
    'perfil_secundario': 'Realista',
    'descripcion': 'Perfil orientado a la investigación, el análisis y la resolución de problemas complejos. '
                   'Disfruta trabajar con ideas abstractas y tiene fuerte inclinación científica.',
    'fortalezas': 'Capacidad analítica\nPensamiento crítico\nRigor metodológico',
    'datos_json': {
        'codigo_riasec': 'IRA',
        'puntajes_por_area': {
            'Realista':      {'Intereses Vocacionales': 4, 'total': 8,  'normalizado': 53.33},
            'Investigador':  {'Intereses Vocacionales': 9, 'total': 12, 'normalizado': 75.00},
            'Artístico':     {'Intereses Vocacionales': 3, 'total': 8,  'normalizado': 37.50},
            'Social':        {'Intereses Vocacionales': 2, 'total': 8,  'normalizado': 25.00},
            'Emprendedor':   {'Intereses Vocacionales': 2, 'total': 8,  'normalizado': 25.00},
            'Convencional':  {'Intereses Vocacionales': 1, 'total': 8,  'normalizado': 12.50},
        },
        'carreras_afines': ['Ingeniería Biomédica', 'Medicina', 'Biología', 'Química', 'Física'],
        'ambiente_trabajo': 'Laboratorios, centros de investigación, universidades y entornos científicos.',
    }
}


def crear_app_completada(usuario_id, config_id, perfil_data, dias_atras=30):
    """Crea una aplicación completada con perfil y resultado de dimensión."""
    fecha_fin = datetime.utcnow() - timedelta(days=dias_atras)
    fecha_inicio = fecha_fin - timedelta(hours=1)

    nueva_app = Aplicacion(
        usuario_id=usuario_id,
        configuracion_id=config_id,
        estado='completada',
        progreso=100,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )
    db.session.add(nueva_app)
    db.session.flush()

    # PerfilVocacional
    pv = PerfilVocacional(
        aplicacion_id=nueva_app.id,
        perfil_principal=perfil_data['perfil_principal'],
        perfil_secundario=perfil_data['perfil_secundario'],
        descripcion=perfil_data['descripcion'],
        fortalezas=perfil_data['fortalezas'],
        datos_json=perfil_data['datos_json'],
    )
    db.session.add(pv)

    # ResultadoDimension para Intereses Vocacionales
    dim = Dimension.query.filter_by(nombre='Intereses Vocacionales').first()
    if dim:
        rd = ResultadoDimension(
            aplicacion_id=nueva_app.id,
            dimension_id=dim.id,
            puntaje_bruto=9,
            puntaje_normalizado=75.0,
            nivel='alto',
        )
        db.session.add(rd)

    return nueva_app


def eliminar_app(usuario_id, config_id):
    """Elimina todas las aplicaciones de un usuario para un config dado (cascade manual)."""
    from sqlalchemy import text
    apps = Aplicacion.query.filter_by(usuario_id=usuario_id, configuracion_id=config_id).all()
    count = 0
    for a in apps:
        app_id = a.id
        # Limpiar tablas que no tienen ON DELETE CASCADE o tienen NOT NULL
        db.session.execute(text('DELETE FROM clustering_asignaciones WHERE aplicacion_id = :id'), {'id': app_id})
        db.session.execute(text('DELETE FROM perfiles_vocacionales WHERE aplicacion_id = :id'), {'id': app_id})
        db.session.execute(text('DELETE FROM resultados_dimension WHERE aplicacion_id = :id'), {'id': app_id})
        db.session.execute(text('DELETE FROM respuestas WHERE aplicacion_id = :id'), {'id': app_id})
        db.session.execute(text('DELETE FROM aplicaciones WHERE id = :id'), {'id': app_id})
        count += 1
    return count


def cambiar_estado(usuario_id, config_id, nuevo_estado, progreso=0):
    """Cambia el estado de la app más reciente de un usuario para un config."""
    app = Aplicacion.query.filter_by(
        usuario_id=usuario_id, configuracion_id=config_id
    ).order_by(Aplicacion.id.desc()).first()
    if app:
        app.estado = nuevo_estado
        app.progreso = progreso
        if nuevo_estado == 'completada':
            app.fecha_fin = datetime.utcnow() - timedelta(days=5)
        return True
    return False


with app.app_context():
    print("=" * 60)
    print("SETUP DEMO — SUSTENTACIÓN")
    print("=" * 60)

    # ── MARÍA FERNANDA (ID=8) ──────────────────────────────────────
    print("\n[1] María Fernanda Rodrig (ID=8)")

    # cfg1 (Intereses): no tiene → crear completada
    existing_cfg1 = Aplicacion.query.filter_by(usuario_id=MARIA_FERNANDA_ID, configuracion_id=CFG_INTERESES).first()
    if not existing_cfg1:
        a = crear_app_completada(MARIA_FERNANDA_ID, CFG_INTERESES, PERFIL_MF, dias_atras=45)
        print(f"  ✓ cfg1 (Intereses) creada → completada (app_id provisional)")
    else:
        existing_cfg1.estado = 'completada'
        existing_cfg1.progreso = 100
        print(f"  ✓ cfg1 (Intereses) ya existía → marcada completada")

    # cfg14 (Seguimiento): eliminar para que quede sin iniciar
    n = eliminar_app(MARIA_FERNANDA_ID, CFG_SEGUIMIENTO)
    print(f"  ✓ cfg14 (Seguimiento) eliminada ({n} app(s)) → sin iniciar")

    db.session.commit()
    print("  Commit OK")

    # ── OTROS ESTUDIANTES — VARIEDAD DE ESTADOS ────────────────────
    print("\n[2] Otros estudiantes — variedad de estados para cfg14")

    # Sin iniciar (eliminar cfg14): estudiantes ID 5, 10
    for uid, nombre in [(5, 'Juan Pérez'), (10, 'Laura Torres')]:
        n = eliminar_app(uid, CFG_SEGUIMIENTO)
        print(f"  {nombre}: cfg14 eliminada ({n} apps) → sin iniciar")

    # En progreso: estudiantes ID 11, 22 (ya tienen completada, cambiar)
    for uid, nombre in [(11, 'Carlos Méndez'), (22, 'Santiago Reyes')]:
        ok = cambiar_estado(uid, CFG_SEGUIMIENTO, 'en_progreso', progreso=45)
        print(f"  {nombre}: cfg14 → en_progreso ({ok})")

    # Abandonada: estudiante ID 13
    ok = cambiar_estado(13, CFG_SEGUIMIENTO, 'abandonada')
    print(f"  Andrés Castillo: cfg14 → abandonada ({ok})")

    # El resto queda completada (ID 6, 14, 16, 18, 19, 25, 26, 28, 29, 31)
    print("  Resto: mantienen cfg14=completada")

    db.session.commit()
    print("\n✓ Todo OK. Estado final:")

    # Mostrar resumen
    from backend.app.models.usuario import Usuario, Rol
    rol = Rol.query.filter_by(nombre='estudiante').first()
    estudiantes = Usuario.query.filter_by(rol_id=rol.id, activo=True).order_by(Usuario.id).all()
    for est in estudiantes:
        apps = Aplicacion.query.filter_by(usuario_id=est.id).order_by(Aplicacion.configuracion_id).all()
        seen = {}
        for a in apps:
            if a.configuracion_id not in seen:
                seen[a.configuracion_id] = a
        def estado_cfg(cid):
            if cid in seen:
                return seen[cid].estado[:4]
            return 'none'
        c1 = estado_cfg(CFG_INTERESES)
        c2 = estado_cfg(CFG_COMPETENCIAS)
        c14 = estado_cfg(CFG_SEGUIMIENTO)
        print(f"  ID={est.id:2d} {est.nombres} {est.apellidos[:12]:12s} | Intereses={c1} Competencias={c2} Seguimiento={c14}")
