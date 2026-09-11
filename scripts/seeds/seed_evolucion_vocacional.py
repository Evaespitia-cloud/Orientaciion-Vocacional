import os
import secrets
DEMO_STUDENT_PASSWORD = os.getenv('DEMO_STUDENT_PASSWORD') or secrets.token_urlsafe(14) + 'Aa1!'
"""
Seed: crea un estudiante con 3 aplicaciones completadas que muestran
una evolución vocacional clara: Convencional → Social → Investigador
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app import create_app
app = create_app()

with app.app_context():
    from backend.app.extensions import db
    from backend.app.models.usuario import Usuario
    from backend.app.models.aplicacion import Aplicacion, ConfiguracionAplicacion
    from backend.app.models.resultado import PerfilVocacional, ResultadoDimension
    from werkzeug.security import generate_password_hash
    from datetime import datetime, timedelta

    EMAIL = 'santiago.reyes@orientacion.edu.co'
    CONFIGS_NOMBRES = [
        'Prueba Holland Semestre 2025-I Reintegro',
        'Prueba Holland Semestre 2025-II Reintegro',
        'Prueba Holland Semestre 2026-I Reintegro',
    ]

    # ── 0. Limpiar datos huérfanos de sesiones fallidas ──────────────────────
    for email_dup in [EMAIL]:
        old = Usuario.query.filter_by(email=email_dup).all()
        if len(old) > 1:
            for o in old[1:]:
                Aplicacion.query.filter_by(usuario_id=o.id).delete()
                db.session.delete(o)
    for nombre_dup in CONFIGS_NOMBRES:
        dups = ConfiguracionAplicacion.query.filter_by(nombre=nombre_dup).all()
        if len(dups) > 1:
            for d in dups[1:]:
                db.session.delete(d)
    db.session.flush()

    # ── 1. Crear estudiante ────────────────────────────────────────────────────
    u = Usuario.query.filter_by(email=EMAIL).first()
    if not u:
        u = Usuario(
            email=EMAIL,
            password_hash=generate_password_hash(DEMO_STUDENT_PASSWORD),
            nombres='Santiago',
            apellidos='Reyes Montoya',
            documento='1095312876',
            tipo_documento='CC',
            rol_id=1,
            activo=True,
        )
        db.session.add(u)
        db.session.flush()
        print(f'Estudiante creado ID={u.id}')
    else:
        print(f'Estudiante ya existe ID={u.id}')

    uid = u.id

    # ── 2. Tres configuraciones históricas ────────────────────────────────────
    from backend.app.models.instrumento import Instrumento
    inst_intereses = Instrumento.query.filter(Instrumento.nombre.like('%Intereses%')).first()
    inst_id_val = inst_intereses.id if inst_intereses else 5
    
    configs_data = [
        ('Prueba Holland Semestre 2025-I Reintegro',  inst_id_val, datetime(2025, 8, 1),  datetime(2025, 10, 31)),
        ('Prueba Holland Semestre 2025-II Reintegro', inst_id_val, datetime(2025, 12, 1), datetime(2026, 2, 28)),
        ('Prueba Holland Semestre 2026-I Reintegro',  inst_id_val, datetime(2026, 3, 1),  datetime(2026, 6, 30)),
    ]
    cfg_ids = []
    for nombre, inst_id, fi, ff in configs_data:
        c = ConfiguracionAplicacion.query.filter_by(nombre=nombre).first()
        if not c:
            c = ConfiguracionAplicacion(
                instrumento_id=inst_id,
                nombre=nombre,
                fecha_inicio=fi,
                fecha_fin=ff,
                activa=False,
                creado_por=1,
            )
            db.session.add(c)
            db.session.flush()
        cfg_ids.append(c.id)
        print(f'Config "{nombre}" ID={c.id}')

    # ── 3. Evolución: 3 momentos ──────────────────────────────────────────────
    etapas = [
        {
            'fecha_fin': datetime(2025, 10, 15, 16, 30),
            'config_id': cfg_ids[0],
            'perfil_principal': 'Convencional',
            'perfil_secundario': 'Social',
            'codigo_riasec': 'CSE',
            'descripcion': (
                'Perfil orientado a la organización, el orden y los sistemas estructurados. '
                'Preferencia por actividades metódicas y predecibles, con leve interés en el trato con personas.'
            ),
            'fortalezas': 'Organización, atención al detalle, seguimiento de procedimientos, manejo de información.',
            'areas_desarrollo': 'Creatividad, iniciativa propia, tolerancia a la incertidumbre.',
            'recomendaciones': 'Explorar carreras como Contaduría, Administración de Empresas o Sistemas de Información.',
            'puntajes': {
                'Convencional': {'bruto': 86, 'normalizado': 0.72},
                'Social':       {'bruto': 65, 'normalizado': 0.54},
                'Emprendedor':  {'bruto': 48, 'normalizado': 0.40},
                'Realista':     {'bruto': 36, 'normalizado': 0.30},
                'Investigador': {'bruto': 33, 'normalizado': 0.28},
                'Art\u00edstico':  {'bruto': 22, 'normalizado': 0.18},
            },
        },
        {
            'fecha_fin': datetime(2026, 1, 22, 14, 10),
            'config_id': cfg_ids[1],
            'perfil_principal': 'Social',
            'perfil_secundario': 'Investigador',
            'codigo_riasec': 'SIC',
            'descripcion': (
                'Transicion hacia el interes por las personas y el conocimiento. '
                'Emergen con fuerza las motivaciones hacia el servicio, la comprension del comportamiento '
                'humano y la indagacion cientifica.'
            ),
            'fortalezas': 'Empatia, comunicacion, trabajo en equipo, curiosidad intelectual creciente.',
            'areas_desarrollo': 'Habilidades analiticas, investigacion, sintesis de informacion.',
            'recomendaciones': (
                'Considerar Psicologia, Trabajo Social, Educacion o carreras de Ciencias Humanas. '
                'Se recomienda participar en grupos de investigacion o semilleros.'
            ),
            'puntajes': {
                'Social':       {'bruto': 82, 'normalizado': 0.68},
                'Investigador': {'bruto': 66, 'normalizado': 0.55},
                'Convencional': {'bruto': 48, 'normalizado': 0.40},
                'Art\u00edstico':  {'bruto': 36, 'normalizado': 0.30},
                'Emprendedor':  {'bruto': 42, 'normalizado': 0.35},
                'Realista':     {'bruto': 30, 'normalizado': 0.25},
            },
        },
        {
            'fecha_fin': datetime(2026, 5, 8, 10, 45),
            'config_id': cfg_ids[2],
            'perfil_principal': 'Investigador',
            'perfil_secundario': 'Social',
            'codigo_riasec': 'ISA',
            'descripcion': (
                'Consolidacion de un perfil cientifico-humanistico. Santiago muestra una marcada orientacion '
                'hacia la investigacion, el analisis critico y la comprension profunda de fenomenos complejos, '
                'manteniendo un solido componente social.'
            ),
            'fortalezas': (
                'Pensamiento analitico, rigor cientifico, capacidad de investigacion, '
                'habilidades interpersonales, comprension sistemica.'
            ),
            'areas_desarrollo': 'Habilidades de liderazgo, comunicacion de resultados, emprendimiento en ciencia.',
            'recomendaciones': (
                'Se recomienda fuertemente Psicologia, Biologia, Medicina, Sociologia o Ciencias de la Educacion. '
                'Alta aptitud para programas de investigacion y posgrado.'
            ),
            'puntajes': {
                'Investigador': {'bruto': 98, 'normalizado': 0.82},
                'Social':       {'bruto': 84, 'normalizado': 0.70},
                'Art\u00edstico':  {'bruto': 60, 'normalizado': 0.50},
                'Emprendedor':  {'bruto': 36, 'normalizado': 0.30},
                'Convencional': {'bruto': 26, 'normalizado': 0.22},
                'Realista':     {'bruto': 22, 'normalizado': 0.18},
            },
        },
    ]

    # ── 4. Limpiar aplicaciones previas ───────────────────────────────────────
    Aplicacion.query.filter_by(usuario_id=uid).delete()
    db.session.flush()

    # ── 5. Crear aplicaciones + resultados + perfiles ─────────────────────────
    for i, etapa in enumerate(etapas, 1):
        ap = Aplicacion(
            usuario_id=uid,
            configuracion_id=etapa['config_id'],
            estado='completada',
            progreso=100,
            fecha_inicio=etapa['fecha_fin'] - timedelta(hours=1),
            fecha_fin=etapa['fecha_fin'],
        )
        db.session.add(ap)
        db.session.flush()

        # Dynamic Dimension lookup
        from backend.app.models.instrumento import Instrumento
        dim = None
        if ap.configuracion and ap.configuracion.instrumento:
            dim = ap.configuracion.instrumento.dimensiones.first()
        dim_id = dim.id if dim else 6
        dim_nombre = dim.nombre if dim else 'Intereses Vocacionales'

        ppal = etapa['puntajes'][etapa['perfil_principal']]
        norm_pct = round(ppal['normalizado'] * 100, 2)
        bruto_val = int(round(ppal['normalizado'] * 30))
        
        rd = ResultadoDimension(
            aplicacion_id=ap.id,
            dimension_id=dim_id,
            puntaje_bruto=bruto_val,
            puntaje_normalizado=norm_pct,
            nivel='muy_alto' if norm_pct >= 80 else 'alto' if norm_pct >= 60 else 'medio' if norm_pct >= 40 else 'bajo',
        )
        db.session.add(rd)

        # PerfilVocacional with robust unified JSON
        pv = PerfilVocacional(
            aplicacion_id=ap.id,
            perfil_principal=etapa['perfil_principal'],
            perfil_secundario=etapa['perfil_secundario'],
            descripcion=etapa['descripcion'],
            fortalezas=etapa['fortalezas'],
            areas_desarrollo=etapa['areas_desarrollo'],
            recomendaciones=etapa['recomendaciones'],
            datos_json={
                'codigo_riasec': etapa['codigo_riasec'],
                'puntajes_por_area': {
                    area: {
                        'positivas': int(round(v['normalizado'] * 5)),
                        'total': 5,
                        'normalizado': round(v['normalizado'] * 100, 2),
                        'Intereses Vocacionales': int(round(v['normalizado'] * 5))
                    }
                    for area, v in etapa['puntajes'].items()
                },
            },
        )
        db.session.add(pv)
        print(f'  [{i}] {etapa["perfil_principal"]}/{etapa["perfil_secundario"]} '
              f'({etapa["fecha_fin"].date()}) ap_id={ap.id}')

    db.session.commit()
    print()
    print('=== LISTO ===')
    print(f'Estudiante : santiago.reyes@orientacion.edu.co  /  {DEMO_STUDENT_PASSWORD}')
    print('Evolucion  : Convencional (Oct-2025) -> Social (Ene-2026) -> Investigador (May-2026)')
    print('Ver en     : Admin > Consulta de Resultados > boton Evolucion de Santiago Reyes Montoya')
