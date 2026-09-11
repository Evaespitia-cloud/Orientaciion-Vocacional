"""
Actualiza los PerfilVocacional de aplicaciones antiguas para que los perfiles
varíen a lo largo del tiempo — mostrando una evolución vocacional realista.

Estrategia:
- La aplicación MÁS RECIENTE de cada estudiante conserva su perfil sin cambios.
- Las aplicaciones anteriores reciben el perfil secundario u otro área como principal,
  simulando que el perfil vocacional se consolida con el tiempo.
"""
import sys, random
from datetime import datetime

sys.path.insert(0, 'backend')
from backend.app import create_app
from backend.app.models.aplicacion import Aplicacion
from backend.app.models.resultado import PerfilVocacional
from backend.app.extensions import db
from sqlalchemy import func

random.seed(99)

RIASEC = ['Realista', 'Investigador', 'Artístico', 'Social', 'Emprendedor', 'Convencional']

CODIGOS = {'R': 'Realista', 'I': 'Investigador', 'A': 'Artístico',
           'S': 'Social', 'E': 'Emprendedor', 'C': 'Convencional'}
LETRAS  = {v: k for k, v in CODIGOS.items()}

DESCRIPCIONES = {
    'Realista':     'Tienes habilidades prácticas y técnicas destacadas. Prefieres trabajar con objetos, herramientas y situaciones concretas.',
    'Investigador': 'Posees una gran curiosidad intelectual y capacidad analítica. Disfrutas investigar, resolver problemas complejos y adquirir conocimientos.',
    'Artístico':    'Tienes gran sensibilidad creativa y necesitas expresarte. Tu fortaleza está en la innovación estética y la comunicación original.',
    'Social':       'Te motiva profundamente ayudar a otros, enseñar y trabajar en equipo. Tienes excelentes habilidades interpersonales.',
    'Emprendedor':  'Tienes aptitudes para el liderazgo, la persuasión y la gestión. Disfrutas asumir riesgos calculados y dirigir proyectos.',
    'Convencional': 'Disfrutas la organización, el orden y los sistemas estructurados. Eres preciso y eficiente en entornos con reglas claras.',
}

app = create_app()

with app.app_context():
    # Obtener estudiantes con más de 1 app completada
    rows = db.session.query(
        Aplicacion.usuario_id,
        func.count(Aplicacion.id).label('n')
    ).filter_by(estado='completada').group_by(Aplicacion.usuario_id).having(func.count(Aplicacion.id) > 1).all()

    print(f"Estudiantes con evolución (>1 app): {len(rows)}")
    actualizados = 0

    for usuario_id, n_apps in rows:
        # Apps ordenadas de más antigua a más reciente
        apps = (Aplicacion.query
                .filter_by(usuario_id=usuario_id, estado='completada')
                .order_by(Aplicacion.fecha_fin)
                .all())

        # Perfil final (más reciente) — no se toca
        pv_final = PerfilVocacional.query.filter_by(aplicacion_id=apps[-1].id).first()
        if not pv_final:
            continue
        perfil_final = pv_final.perfil_principal
        secundario_final = pv_final.perfil_secundario

        # Índices de apps a modificar (todas menos la última)
        for idx, ap in enumerate(apps[:-1]):
            pv = PerfilVocacional.query.filter_by(aplicacion_id=ap.id).first()
            if not pv:
                continue

            n_restantes = len(apps) - 1 - idx  # distancia a la última

            # Decidir el nuevo perfil principal según posición:
            # - Primera prueba: usar perfil secundario ó un área diferente del final
            # - Pruebas intermedias: alternar entre secundario y final
            otros = [a for a in RIASEC if a != perfil_final]

            if n_restantes >= 3:
                # Muy antiguo: usa un perfil diferente (secundario o aleatorio de los otros)
                candidatos = [a for a in RIASEC if a != perfil_final]
                # Priorizar el secundario si existe
                if secundario_final and secundario_final in candidatos:
                    nuevo_principal = secundario_final
                    nuevo_secundario = random.choice([a for a in candidatos if a != nuevo_principal])
                else:
                    nuevo_principal = random.choice(candidatos[:3])
                    nuevo_secundario = random.choice([a for a in candidatos if a != nuevo_principal])
            elif n_restantes == 2:
                # Intermedio: secundario pasa a principal
                if secundario_final:
                    nuevo_principal = secundario_final
                    nuevo_secundario = random.choice([a for a in RIASEC if a not in (nuevo_principal, perfil_final)])
                else:
                    candidatos = [a for a in RIASEC if a != perfil_final]
                    nuevo_principal = random.choice(candidatos)
                    nuevo_secundario = perfil_final
            else:
                # n_restantes == 1 (segunda a última): puede ser secundario o el mismo final
                # 60% que ya muestre el perfil final, 40% que muestre el secundario
                if random.random() < 0.4 and secundario_final:
                    nuevo_principal = secundario_final
                    nuevo_secundario = perfil_final
                else:
                    nuevo_principal = perfil_final
                    nuevo_secundario = secundario_final
                    # No hay cambio real, skip
                    continue

            # Recalcular código RIASEC con nuevo orden
            letra1 = LETRAS.get(nuevo_principal, '?')
            letra2 = LETRAS.get(nuevo_secundario, '?') if nuevo_secundario else ''
            # Tercer código: el más frecuente que no sea los dos anteriores
            otros_codigos = [LETRAS[a] for a in RIASEC if a not in (nuevo_principal, nuevo_secundario)]
            letra3 = random.choice(otros_codigos) if otros_codigos else ''
            nuevo_codigo = letra1 + letra2 + letra3

            # Actualizar pv
            pv.perfil_principal = nuevo_principal
            pv.perfil_secundario = nuevo_secundario
            pv.descripcion = DESCRIPCIONES[nuevo_principal]

            if pv.datos_json:
                datos = dict(pv.datos_json)
                datos['codigo_riasec'] = nuevo_codigo
                pv.datos_json = datos

            actualizados += 1

    db.session.commit()
    print(f"✓ Perfiles actualizados: {actualizados}")

    # Verificar resultado
    print("\nVerificación (primeros 5 estudiantes):")
    rows2 = db.session.query(
        Aplicacion.usuario_id,
        func.count(Aplicacion.id).label('n')
    ).filter_by(estado='completada').group_by(Aplicacion.usuario_id).having(func.count(Aplicacion.id) > 1).limit(5).all()

    for usuario_id, _ in rows2:
        apps = (Aplicacion.query.filter_by(usuario_id=usuario_id, estado='completada')
                .order_by(Aplicacion.fecha_fin).all())
        perfiles = []
        for a in apps:
            pv = PerfilVocacional.query.filter_by(aplicacion_id=a.id).first()
            codigo = (pv.datos_json or {}).get('codigo_riasec', '?') if pv else '?'
            perfiles.append(f"{pv.perfil_principal if pv else 'N/A'} ({codigo})")
        print(f"  user {usuario_id}: {' → '.join(perfiles)}")
