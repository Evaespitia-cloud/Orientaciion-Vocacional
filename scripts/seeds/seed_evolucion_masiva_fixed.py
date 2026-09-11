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
    # 0 — Social puro: vocación clara en relaciones humanas (docencia, trabajo social)
    [
        {'Realista':0.15,'Investigador':0.20,'Artístico':0.25,'Social':0.88,'Emprendedor':0.20,'Convencional':0.15},
        {'Realista':0.12,'Investigador':0.18,'Artístico':0.22,'Social':0.92,'Emprendedor':0.25,'Convencional':0.15},
        {'Realista':0.12,'Investigador':0.18,'Artístico':0.20,'Social':0.95,'Emprendedor':0.28,'Convencional':0.15},
    ],
    # 1 — Investigador puro: ciencias exactas, pensamiento analítico
    [
        {'Realista':0.22,'Investigador':0.88,'Artístico':0.18,'Social':0.20,'Emprendedor':0.15,'Convencional':0.20},
        {'Realista':0.18,'Investigador':0.92,'Artístico':0.15,'Social':0.18,'Emprendedor':0.12,'Convencional':0.18},
        {'Realista':0.15,'Investigador':0.95,'Artístico':0.15,'Social':0.15,'Emprendedor':0.12,'Convencional':0.15},
    ],
    # 2 — Emprendedor puro: liderazgo, negocios, persuasión
    [
        {'Realista':0.18,'Investigador':0.15,'Artístico':0.20,'Social':0.30,'Emprendedor':0.90,'Convencional':0.22},
        {'Realista':0.15,'Investigador':0.12,'Artístico':0.18,'Social':0.28,'Emprendedor':0.93,'Convencional':0.20},
        {'Realista':0.12,'Investigador':0.12,'Artístico':0.15,'Social':0.25,'Emprendedor':0.95,'Convencional':0.18},
    ],
    # 3 — Realista puro: habilidades técnicas manuales, ingeniería aplicada
    [
        {'Realista':0.90,'Investigador':0.28,'Artístico':0.12,'Social':0.12,'Emprendedor':0.18,'Convencional':0.25},
        {'Realista':0.93,'Investigador':0.25,'Artístico':0.10,'Social':0.10,'Emprendedor':0.15,'Convencional':0.28},
        {'Realista':0.95,'Investigador':0.25,'Artístico':0.10,'Social':0.10,'Emprendedor':0.12,'Convencional':0.30},
    ],
    # 4 — Artístico puro: expresión creativa, diseño, artes
    [
        {'Realista':0.15,'Investigador':0.20,'Artístico':0.90,'Social':0.28,'Emprendedor':0.18,'Convencional':0.12},
        {'Realista':0.12,'Investigador':0.18,'Artístico':0.93,'Social':0.25,'Emprendedor':0.15,'Convencional':0.10},
        {'Realista':0.12,'Investigador':0.18,'Artístico':0.95,'Social':0.22,'Emprendedor':0.15,'Convencional':0.10},
    ],
    # 5 — Convencional puro: organización, administración, normas
    [
        {'Realista':0.25,'Investigador':0.18,'Artístico':0.12,'Social':0.22,'Emprendedor':0.28,'Convencional':0.90},
        {'Realista':0.22,'Investigador':0.15,'Artístico':0.10,'Social':0.20,'Emprendedor':0.25,'Convencional':0.93},
        {'Realista':0.20,'Investigador':0.15,'Artístico':0.10,'Social':0.18,'Emprendedor':0.22,'Convencional':0.95},
    ],
    # 6 — Investigador-Artístico: perfil científico-creativo (diseño industrial, arquitectura)
    [
        {'Realista':0.18,'Investigador':0.82,'Artístico':0.80,'Social':0.18,'Emprendedor':0.12,'Convencional':0.12},
        {'Realista':0.15,'Investigador':0.85,'Artístico':0.83,'Social':0.15,'Emprendedor':0.12,'Convencional':0.12},
        {'Realista':0.15,'Investigador':0.88,'Artístico':0.85,'Social':0.15,'Emprendedor':0.10,'Convencional':0.10},
    ],
    # 7 — Social-Emprendedor: liderazgo humanista (psicología organizacional, RRHH)
    [
        {'Realista':0.15,'Investigador':0.18,'Artístico':0.20,'Social':0.82,'Emprendedor':0.80,'Convencional':0.20},
        {'Realista':0.12,'Investigador':0.15,'Artístico':0.18,'Social':0.85,'Emprendedor':0.83,'Convencional':0.18},
        {'Realista':0.12,'Investigador':0.15,'Artístico':0.15,'Social':0.88,'Emprendedor':0.85,'Convencional':0.18},
    ],
    # 8 — Realista-Investigador: ingeniería científica (biomédica, sistemas)
    [
        {'Realista':0.80,'Investigador':0.82,'Artístico':0.12,'Social':0.12,'Emprendedor':0.15,'Convencional':0.22},
        {'Realista':0.83,'Investigador':0.85,'Artístico':0.10,'Social':0.10,'Emprendedor':0.12,'Convencional':0.20},
        {'Realista':0.85,'Investigador':0.88,'Artístico':0.10,'Social':0.10,'Emprendedor':0.12,'Convencional':0.18},
    ],
    # 9 — Emprendedor-Convencional: gestión empresarial, finanzas, contabilidad
    [
        {'Realista':0.15,'Investigador':0.18,'Artístico':0.12,'Social':0.25,'Emprendedor':0.82,'Convencional':0.80},
        {'Realista':0.12,'Investigador':0.15,'Artístico':0.10,'Social':0.22,'Emprendedor':0.85,'Convencional':0.83},
        {'Realista':0.12,'Investigador':0.12,'Artístico':0.10,'Social':0.20,'Emprendedor':0.88,'Convencional':0.85},
    ],
]

# ─── Estados por estudiante (asignados cíclicamente por orden) ────────────── #
# 'ccc' = 3 completadas | 'ccp' = 2 completadas + 1 en_progreso
# 'cap' = 1 completada + 1 abandonada + 1 en_progreso | 'aaa' = todas abandonadas
# 'cc'  = solo 2 completadas (por si el 3er periodo aún no inició)
ESTADOS_CICLO = [
    'ccc',   # 0
    'ccc',   # 1
    'ccc',   # 2
    'ccp',   # 3 — tiene en progreso
    'ccc',   # 4
    'ccc',   # 5
    'cap',   # 6 — 1 completa, 1 abandonada, 1 en progreso
    'ccc',   # 7
    'ccc',   # 8
    'aaa',   # 9 — todas abandonadas
    'ccc',   # 10
    'ccp',   # 11
    'ccc',   # 12
]

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
            for escala in dimension.escalas:
                area = escala.nombre
                peso = pesos.get(area, 0.5)
                for item in escala.items:
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

        for orden, estudiante in enumerate(estudiantes):
            patron_idx    = orden % len(PATRONES_EVOLUCION)
            estado_codigo = ESTADOS_CICLO[orden % len(ESTADOS_CICLO)]
            patron        = PATRONES_EVOLUCION[patron_idx]

            print(f"▶ [{estudiante.id}] {f"{estudiante.nombres} {estudiante.apellidos}"} — patrón {patron_idx}, estado: {estado_codigo}")

            for p_idx, config in enumerate(configs):
                # Saltar si ya existe alguna app para este par estudiante+config
                if ya_tiene_app(estudiante.id, config.id):
                    print(f"      ⚠  P{p_idx+1} ya existe, omitido")
                    continue

                pesos = patron[p_idx]

                if estado_codigo == 'ccc':
                    # 3 completadas
                    simular_completada(estudiante, config, pesos, app, p_idx)

                elif estado_codigo == 'ccp':
                    # P1 y P2 completadas, P3 en progreso
                    if p_idx < 2:
                        simular_completada(estudiante, config, pesos, app, p_idx)
                    else:
                        crear_en_progreso(estudiante, config, p_idx)

                elif estado_codigo == 'cap':
                    # P1 completada, P2 abandonada, P3 en progreso
                    if p_idx == 0:
                        simular_completada(estudiante, config, pesos, app, p_idx)
                    elif p_idx == 1:
                        crear_abandonada(estudiante, config, p_idx)
                    else:
                        crear_en_progreso(estudiante, config, p_idx)

                elif estado_codigo == 'aaa':
                    # Todas abandonadas
                    crear_abandonada(estudiante, config, p_idx)

            print()

        print("=" * 60)
        print("✓ Seed de evolución completado.")
        print(f"  Configuraciones creadas: {[c.nombre[-20:] for c in configs]}")
        print(f"  Estudiantes procesados:  {len(estudiantes)}")
        print("=" * 60)


if __name__ == '__main__':
    main()
