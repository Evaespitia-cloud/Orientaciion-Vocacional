"""
Seed de evolución vocacional masiva — 3 periodos históricos para TODOS los estudiantes.

Periodos:
  P1 → Octubre 2025    (primer acercamiento)
  P2 → Enero  2026     (seguimiento de mitad de año)
  P3 → Mayo   2026     (evaluación final)

Cada estudiante tiene un patrón de evolución único (el perfil puede cambiar o consolidarse).
Estados variados:
  - La mayoría: 3 pruebas completadas
  - Algunos:    2 completadas + 1 en progreso
  - Algunos:    1 completada + 1 abandonada + 1 en progreso
  - Pocos:      todas abandonadas (ninguna completada)
"""
import sys
import random
import json
from datetime import datetime, timedelta

sys.path.insert(0, '.')

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models.usuario import Usuario, Rol
from backend.app.models.aplicacion import Aplicacion, Respuesta, ConfiguracionAplicacion
from backend.app.models.instrumento import Instrumento, Escala
from backend.app.services.psicometrico_service import PsicometricoService

random.seed(2026_05_18)

# ─── Patrones de evolución ────────────────────────────────────────────────── #
# Cada patrón tiene 3 sets de pesos (uno por periodo).
# El perfil dominante de cada set determina el resultado calculado.
PATRONES_EVOLUCION = [
    # 0 — Social sólido, se consolida con Emprendedor
    [
        {'Realista':0.25,'Investigador':0.35,'Artístico':0.55,'Social':0.85,'Emprendedor':0.5,'Convencional':0.3},
        {'Realista':0.2, 'Investigador':0.3,'Artístico':0.5, 'Social':0.9, 'Emprendedor':0.65,'Convencional':0.3},
        {'Realista':0.2, 'Investigador':0.35,'Artístico':0.45,'Social':0.85,'Emprendedor':0.8,'Convencional':0.3},
    ],
    # 1 — Investigador emergente (empieza mixto, consolida Investigador)
    [
        {'Realista':0.4, 'Investigador':0.6,'Artístico':0.4,'Social':0.5,'Emprendedor':0.35,'Convencional':0.45},
        {'Realista':0.35,'Investigador':0.75,'Artístico':0.35,'Social':0.45,'Emprendedor':0.3,'Convencional':0.4},
        {'Realista':0.3, 'Investigador':0.9,'Artístico':0.3,'Social':0.4,'Emprendedor':0.25,'Convencional':0.35},
    ],
    # 2 — Emprendedor constante y creciente
    [
        {'Realista':0.35,'Investigador':0.3,'Artístico':0.45,'Social':0.55,'Emprendedor':0.75,'Convencional':0.6},
        {'Realista':0.3, 'Investigador':0.25,'Artístico':0.4,'Social':0.5, 'Emprendedor':0.85,'Convencional':0.65},
        {'Realista':0.25,'Investigador':0.2,'Artístico':0.35,'Social':0.45,'Emprendedor':0.95,'Convencional':0.7},
    ],
    # 3 — Realista técnico, se mantiene firme
    [
        {'Realista':0.85,'Investigador':0.5,'Artístico':0.2,'Social':0.25,'Emprendedor':0.4,'Convencional':0.55},
        {'Realista':0.9, 'Investigador':0.55,'Artístico':0.15,'Social':0.2,'Emprendedor':0.35,'Convencional':0.6},
        {'Realista':0.95,'Investigador':0.6,'Artístico':0.15,'Social':0.2,'Emprendedor':0.3,'Convencional':0.65},
    ],
    # 4 — Artístico-Investigador, evolución creativa-científica
    [
        {'Realista':0.2,'Investigador':0.65,'Artístico':0.75,'Social':0.45,'Emprendedor':0.3,'Convencional':0.2},
        {'Realista':0.2,'Investigador':0.7,'Artístico':0.8,'Social':0.4,'Emprendedor':0.3,'Convencional':0.2},
        {'Realista':0.2,'Investigador':0.8,'Artístico':0.85,'Social':0.35,'Emprendedor':0.25,'Convencional':0.2},
    ],
    # 5 — Convencional con pico Realista al final
    [
        {'Realista':0.5,'Investigador':0.35,'Artístico':0.3,'Social':0.4,'Emprendedor':0.45,'Convencional':0.8},
        {'Realista':0.6,'Investigador':0.3,'Artístico':0.25,'Social':0.35,'Emprendedor':0.4,'Convencional':0.85},
        {'Realista':0.75,'Investigador':0.3,'Artístico':0.2,'Social':0.3,'Emprendedor':0.4,'Convencional':0.9},
    ],
    # 6 — Social baja, Emprendedor sube (cambio vocacional notable)
    [
        {'Realista':0.3,'Investigador':0.35,'Artístico':0.4,'Social':0.85,'Emprendedor':0.4,'Convencional':0.3},
        {'Realista':0.3,'Investigador':0.4,'Artístico':0.45,'Social':0.65,'Emprendedor':0.7,'Convencional':0.35},
        {'Realista':0.3,'Investigador':0.4,'Artístico':0.5,'Social':0.45,'Emprendedor':0.9,'Convencional':0.4},
    ],
    # 7 — Perfil mixto que se define hacia Artístico
    [
        {'Realista':0.4,'Investigador':0.5,'Artístico':0.6,'Social':0.55,'Emprendedor':0.4,'Convencional':0.3},
        {'Realista':0.3,'Investigador':0.45,'Artístico':0.75,'Social':0.5,'Emprendedor':0.35,'Convencional':0.25},
        {'Realista':0.25,'Investigador':0.4,'Artístico':0.9,'Social':0.45,'Emprendedor':0.3,'Convencional':0.2},
    ],
    # 8 — Investigador-Social (ciencias de la salud)
    [
        {'Realista':0.3,'Investigador':0.7,'Artístico':0.3,'Social':0.75,'Emprendedor':0.3,'Convencional':0.35},
        {'Realista':0.25,'Investigador':0.8,'Artístico':0.25,'Social':0.8,'Emprendedor':0.25,'Convencional':0.3},
        {'Realista':0.2,'Investigador':0.85,'Artístico':0.25,'Social':0.85,'Emprendedor':0.2,'Convencional':0.3},
    ],
    # 9 — Convencional-Emprendedor (negocios y gestión)
    [
        {'Realista':0.3,'Investigador':0.3,'Artístico':0.25,'Social':0.5,'Emprendedor':0.7,'Convencional':0.8},
        {'Realista':0.25,'Investigador':0.25,'Artístico':0.2,'Social':0.45,'Emprendedor':0.8,'Convencional':0.85},
        {'Realista':0.2,'Investigador':0.25,'Artístico':0.2,'Social':0.4,'Emprendedor':0.9,'Convencional':0.9},
    ],
]


# Asignar 90% de estudiantes con 3 pruebas completadas ('ccc'), el resto con otros estados
def get_estado_ciclo(n_estudiantes):
    n_ccc = int(n_estudiantes * 0.9)
    estados = ['ccc'] * n_ccc
    resto = n_estudiantes - n_ccc
    otros = ['ccp', 'cap', 'aaa']
    for i in range(resto):
        estados.append(otros[i % len(otros)])
    return estados

# ─── Fechas de los 3 periodos ─────────────────────────────────────────────── #
# P1: Oct 2025 | P2: Ene 2026 | P3: May 2026
HOY = datetime.utcnow()
PERIODOS = [
    {'nombre': 'Evaluación Vocacional — Periodo I (2025)',    'inicio': HOY - timedelta(days=215), 'fin': HOY - timedelta(days=180)},
    {'nombre': 'Evaluación Vocacional — Periodo II (2026)',   'inicio': HOY - timedelta(days=120), 'fin': HOY - timedelta(days=90)},
    {'nombre': 'Evaluación Vocacional — Periodo III (2026)',  'inicio': HOY - timedelta(days=20),  'fin': HOY + timedelta(days=30)},
]


def get_or_create_configs(instrumento, admin_id):
    """Devuelve las 3 configuraciones de evolución, creándolas si no existen."""
    configs = []
    for p in PERIODOS:
        c = ConfiguracionAplicacion.query.filter_by(nombre=p['nombre']).first()
        if not c:
            c = ConfiguracionAplicacion(
                instrumento_id=instrumento.id,
                nombre=p['nombre'],
                descripcion='Periodo de evaluación vocacional simulado para seguimiento longitudinal.',
                fecha_inicio=p['inicio'],
                fecha_fin=p['fin'],
                obligatoria=False,
                activa=True,
                cohorte='2026',
                creado_por=admin_id,
            )
            db.session.add(c)
            db.session.flush()
            print(f"  + Configuración creada: {c.nombre[:60]}")
        else:
            print(f"  ✓ Ya existe: {c.nombre[:60]}")
        configs.append(c)
    db.session.commit()
    return configs


def simular_completada(usuario, config, pesos, app_ctx, periodo_idx):
    """Crea una aplicación completada con respuestas y perfil calculado."""
    with app_ctx.app_context():
        # Fecha de la prueba: dentro del periodo
        p = PERIODOS[periodo_idx]
        delta_total = int((p['fin'] - p['inicio']).days)
        offset = random.randint(0, max(0, delta_total - 1))
        fecha_inicio = p['inicio'] + timedelta(days=offset, hours=random.randint(7, 17))
        fecha_fin    = fecha_inicio + timedelta(minutes=random.randint(14, 28))

        ap = Aplicacion(
            usuario_id=usuario.id,
            configuracion_id=config.id,
            estado='completada',
            ip_address='127.0.0.1',
            user_agent='SeedEvolucion/2.0',
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )
        db.session.add(ap)
        db.session.flush()

        # Respuestas

        for dimension in config.instrumento.dimensiones:
            # Si es la dimensión de competencias, siempre responde positivo (simula alto desempeño)
            if 'competenc' in dimension.nombre.lower():
                peso_comp = 0.95
            else:
                peso_comp = None
            for escala in dimension.escalas:
                area = escala.nombre
                peso = pesos.get(area, 0.5) if peso_comp is None else peso_comp
                # RESPONDER TODOS LOS ÍTEMS ACTIVOS DE LA ESCALA
                for item in escala.items.filter_by(activo=True):
                    if item.tipo in ('binario', 'eleccion_forzada'):
                        val = 1 if random.random() < peso else 0
                        texto = 'Sí' if val == 1 else 'No'
                    else:
                        opciones = item.opciones if isinstance(item.opciones, dict) else json.loads(item.opciones or '{}')
                        lista = opciones.get('opciones', [])
                        correcta = next((i for i, o in enumerate(lista) if o.get('valor') == 1), 0)
                        incorrectas = [i for i, o in enumerate(lista) if o.get('valor') != 1]
                        val = correcta if random.random() < peso else (random.choice(incorrectas) if incorrectas else correcta)
                        texto = str(val)

                    db.session.add(Respuesta(
                        aplicacion_id=ap.id,
                        item_id=item.id,
                        valor=val,
                        valor_texto=texto,
                        tiempo_respuesta_seg=random.randint(3, 14),
                    ))
        db.session.commit()

        try:
            PsicometricoService.calcular_puntajes_dimension(ap.id)
            perfil = PsicometricoService.generar_perfil(ap.id)
            fecha_str = fecha_fin.strftime('%Y-%m-%d')
            print(f"      ✓ P{periodo_idx+1} [{fecha_str}] → {perfil.perfil_principal}/{perfil.perfil_secundario}")
            return ap
        except Exception as e:
            print(f"      ✗ Error calculando perfil P{periodo_idx+1}: {e}")
            db.session.rollback()
            return None


def crear_en_progreso(usuario, config, periodo_idx):
    """Crea una aplicación en progreso (sin completar)."""
    p = PERIODOS[periodo_idx]
    delta_total = int((p['fin'] - p['inicio']).days)
    offset = random.randint(0, max(0, delta_total - 1))
    fecha_inicio = p['inicio'] + timedelta(days=offset, hours=random.randint(7, 17))

    ap = Aplicacion(
        usuario_id=usuario.id,
        configuracion_id=config.id,
        estado='en_progreso',
        progreso=random.randint(20, 65),
        ip_address='127.0.0.1',
        user_agent='SeedEvolucion/2.0',
        fecha_inicio=fecha_inicio,
    )
    db.session.add(ap)
    db.session.commit()
    print(f"      ~ P{periodo_idx+1} [{fecha_inicio.strftime('%Y-%m-%d')}] → EN PROGRESO ({ap.progreso}%)")


def crear_abandonada(usuario, config, periodo_idx):
    """Crea una aplicación abandonada."""
    p = PERIODOS[periodo_idx]
    delta_total = int((p['fin'] - p['inicio']).days)
    offset = random.randint(0, max(0, delta_total - 1))
    fecha_inicio = p['inicio'] + timedelta(days=offset, hours=random.randint(7, 17))

    ap = Aplicacion(
        usuario_id=usuario.id,
        configuracion_id=config.id,
        estado='abandonada',
        progreso=random.randint(5, 25),
        ip_address='127.0.0.1',
        user_agent='SeedEvolucion/2.0',
        fecha_inicio=fecha_inicio,
    )
    db.session.add(ap)
    db.session.commit()
    print(f"      ✗ P{periodo_idx+1} [{fecha_inicio.strftime('%Y-%m-%d')}] → ABANDONADA ({ap.progreso}%)")


def ya_tiene_app(usuario_id, config_id):
    """Verifica si ya existe cualquier aplicación para este estudiante+config."""
    return Aplicacion.query.filter_by(
        usuario_id=usuario_id,
        configuracion_id=config_id,
    ).first() is not None


def main():
    app = create_app()

    with app.app_context():
        # ── Instrumento base ──────────────────────────────────────────────── #
        instrumento = Instrumento.query.filter_by(activo=True).first()
        if not instrumento:
            print("ERROR: No hay instrumentos activos. Ejecuta seed_instruments.py primero.")
            return
        print(f"Instrumento: [{instrumento.id}] {instrumento.nombre}\n")

        # ── Admin para creado_por ─────────────────────────────────────────── #
        admin = Usuario.query.join(Rol).filter(Rol.nombre == 'ti').first()
        admin_id = admin.id if admin else None

        # ── Crear/recuperar las 3 configuraciones de evolución ────────────── #
        print("=== Configuraciones de evolución ===")
        configs = get_or_create_configs(instrumento, admin_id)
        print()

        # ── Obtener todos los estudiantes activos ─────────────────────────── #
        estudiantes = (
            Usuario.query
            .join(Rol)
            .filter(Rol.nombre == 'estudiante', Usuario.activo == True)
            .order_by(Usuario.id)
            .all()
        )
        print(f"=== Procesando {len(estudiantes)} estudiantes ===\n")


        estados_ciclo = get_estado_ciclo(len(estudiantes))


        # FORZAR que todos los estudiantes tengan las dos pruebas obligatorias respondidas como completadas
        for orden, estudiante in enumerate(estudiantes):
            patron_idx    = orden % len(PATRONES_EVOLUCION)
            patron        = PATRONES_EVOLUCION[patron_idx]

            print(f"▶ [{estudiante.id}] {estudiante.nombres} {estudiante.apellidos} — patrón {patron_idx}, estado: OBLIGATORIO")

            for p_idx, config in enumerate(configs):
                # Elimina cualquier aplicación previa para este estudiante y config
                prev_apps = Aplicacion.query.filter_by(usuario_id=estudiante.id, configuracion_id=config.id).all()
                for ap in prev_apps:
                    # Elimina respuestas, perfiles y resultados asociados
                    from backend.app.models.resultado import PerfilVocacional, ResultadoDimension
                    from backend.app.models.aplicacion import Respuesta
                    Respuesta.query.filter_by(aplicacion_id=ap.id).delete()
                    PerfilVocacional.query.filter_by(aplicacion_id=ap.id).delete()
                    ResultadoDimension.query.filter_by(aplicacion_id=ap.id).delete()
                    db.session.delete(ap)
                db.session.commit()

                # Siempre crear como completada
                pesos = patron[p_idx]
                simular_completada(estudiante, config, pesos, app, p_idx)

            print()

        print("=" * 60)
        print("✓ Seed de evolución completado.")
        print(f"  Configuraciones creadas: {[c.nombre[-20:] for c in configs]}")
        print(f"  Estudiantes procesados:  {len(estudiantes)}")
        print("=" * 60)


if __name__ == '__main__':
    main()
