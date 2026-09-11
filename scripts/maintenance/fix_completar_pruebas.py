"""
Fix: Completa las pruebas de TODOS los estudiantes de ejemplo.

Acciones:
  1. Para cada estudiante y cada uno de los 3 periodos de evolución:
     - Si la aplicación es "abandonada" o "en_progreso" → la elimina y crea una completada
     - Si la aplicación es "completada" pero tiene ResultadoDimension con datos nulos → re-calcula
     - Si no existe ninguna aplicación para ese periodo → crea una completada
  2. Garantiza que todos los estudiantes tengan 3 aplicaciones completadas con perfil RIASEC válido.
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
from backend.app.models.resultado import ResultadoDimension, PerfilVocacional
from backend.app.models.instrumento import Instrumento
from backend.app.services.psicometrico_service import PsicometricoService

random.seed(20260518)

# Nombres de los 3 periodos creados por seed_evolucion_masiva.py
NOMBRES_PERIODOS = [
    'Evaluación Vocacional — Periodo I (2025)',
    'Evaluación Vocacional — Periodo II (2026)',
    'Evaluación Vocacional — Periodo III (2026)',
]

# Patrones de evolución con pesos muy diferenciados para garantizar variedad real.
# El área dominante recibe 0.92-0.97; las demás 0.08-0.35.
# 12 patrones distintos para 24 estudiantes → cada patrón se repite exactamente 2 veces.
PATRONES_EVOLUCION = [
    # 0 — Social consolidado
    [
        {'Realista':0.10,'Investigador':0.20,'Artístico':0.30,'Social':0.92,'Emprendedor':0.25,'Convencional':0.15},
        {'Realista':0.10,'Investigador':0.20,'Artístico':0.28,'Social':0.94,'Emprendedor':0.35,'Convencional':0.15},
        {'Realista':0.10,'Investigador':0.22,'Artístico':0.25,'Social':0.95,'Emprendedor':0.45,'Convencional':0.12},
    ],
    # 1 — Investigador emergente
    [
        {'Realista':0.20,'Investigador':0.75,'Artístico':0.25,'Social':0.30,'Emprendedor':0.15,'Convencional':0.20},
        {'Realista':0.18,'Investigador':0.88,'Artístico':0.20,'Social':0.28,'Emprendedor':0.12,'Convencional':0.18},
        {'Realista':0.15,'Investigador':0.95,'Artístico':0.15,'Social':0.25,'Emprendedor':0.10,'Convencional':0.15},
    ],
    # 2 — Emprendedor creciente
    [
        {'Realista':0.18,'Investigador':0.15,'Artístico':0.22,'Social':0.35,'Emprendedor':0.80,'Convencional':0.40},
        {'Realista':0.15,'Investigador':0.12,'Artístico':0.20,'Social':0.30,'Emprendedor':0.90,'Convencional':0.40},
        {'Realista':0.12,'Investigador':0.10,'Artístico':0.18,'Social':0.25,'Emprendedor':0.96,'Convencional':0.38},
    ],
    # 3 — Artístico puro
    [
        {'Realista':0.10,'Investigador':0.30,'Artístico':0.88,'Social':0.28,'Emprendedor':0.15,'Convencional':0.08},
        {'Realista':0.08,'Investigador':0.28,'Artístico':0.92,'Social':0.25,'Emprendedor':0.12,'Convencional':0.08},
        {'Realista':0.08,'Investigador':0.30,'Artístico':0.96,'Social':0.22,'Emprendedor':0.10,'Convencional':0.08},
    ],
    # 4 — Convencional firme con algo de Realista
    [
        {'Realista':0.42,'Investigador':0.18,'Artístico':0.12,'Social':0.20,'Emprendedor':0.22,'Convencional':0.88},
        {'Realista':0.45,'Investigador':0.15,'Artístico':0.10,'Social':0.18,'Emprendedor':0.20,'Convencional':0.92},
        {'Realista':0.35,'Investigador':0.12,'Artístico':0.08,'Social':0.15,'Emprendedor':0.18,'Convencional':0.95},
    ],
    # 5 — Social → Emprendedor (cambio vocacional)
    [
        {'Realista':0.15,'Investigador':0.20,'Artístico':0.25,'Social':0.90,'Emprendedor':0.30,'Convencional':0.18},
        {'Realista':0.15,'Investigador':0.22,'Artístico':0.28,'Social':0.65,'Emprendedor':0.78,'Convencional':0.20},
        {'Realista':0.15,'Investigador':0.22,'Artístico':0.30,'Social':0.30,'Emprendedor':0.93,'Convencional':0.22},
    ],
    # 6 — Investigador-Social (ciencias de la salud)
    [
        {'Realista':0.18,'Investigador':0.82,'Artístico':0.18,'Social':0.80,'Emprendedor':0.15,'Convencional':0.20},
        {'Realista':0.15,'Investigador':0.88,'Artístico':0.15,'Social':0.82,'Emprendedor':0.12,'Convencional':0.18},
        {'Realista':0.12,'Investigador':0.92,'Artístico':0.12,'Social':0.85,'Emprendedor':0.10,'Convencional':0.15},
    ],
    # 7 — Artístico-Investigador (diseño científico)
    [
        {'Realista':0.12,'Investigador':0.68,'Artístico':0.78,'Social':0.28,'Emprendedor':0.15,'Convencional':0.10},
        {'Realista':0.10,'Investigador':0.72,'Artístico':0.85,'Social':0.25,'Emprendedor':0.12,'Convencional':0.10},
        {'Realista':0.10,'Investigador':0.78,'Artístico':0.90,'Social':0.22,'Emprendedor':0.10,'Convencional':0.08},
    ],
    # 8 — Emprendedor-Convencional (negocios y gestión)
    [
        {'Realista':0.15,'Investigador':0.15,'Artístico':0.12,'Social':0.30,'Emprendedor':0.82,'Convencional':0.78},
        {'Realista':0.12,'Investigador':0.12,'Artístico':0.10,'Social':0.28,'Emprendedor':0.88,'Convencional':0.82},
        {'Realista':0.10,'Investigador':0.10,'Artístico':0.08,'Social':0.25,'Emprendedor':0.94,'Convencional':0.85},
    ],
    # 9 — Realista técnico (único patrón Realista)
    [
        {'Realista':0.88,'Investigador':0.40,'Artístico':0.10,'Social':0.15,'Emprendedor':0.22,'Convencional':0.45},
        {'Realista':0.92,'Investigador':0.42,'Artístico':0.08,'Social':0.12,'Emprendedor':0.20,'Convencional':0.48},
        {'Realista':0.96,'Investigador':0.45,'Artístico':0.08,'Social':0.10,'Emprendedor':0.18,'Convencional':0.50},
    ],
    # 10 — Social-Artístico (comunicación y humanidades)
    [
        {'Realista':0.10,'Investigador':0.25,'Artístico':0.72,'Social':0.80,'Emprendedor':0.28,'Convencional':0.12},
        {'Realista':0.08,'Investigador':0.22,'Artístico':0.78,'Social':0.82,'Emprendedor':0.25,'Convencional':0.10},
        {'Realista':0.08,'Investigador':0.20,'Artístico':0.82,'Social':0.85,'Emprendedor':0.22,'Convencional':0.08},
    ],
    # 11 — Investigador consolidado desde el inicio
    [
        {'Realista':0.25,'Investigador':0.90,'Artístico':0.22,'Social':0.35,'Emprendedor':0.18,'Convencional':0.22},
        {'Realista':0.22,'Investigador':0.93,'Artístico':0.18,'Social':0.32,'Emprendedor':0.15,'Convencional':0.20},
        {'Realista':0.18,'Investigador':0.96,'Artístico':0.15,'Social':0.28,'Emprendedor':0.12,'Convencional':0.18},
    ],
]


def _borrar_app(ap):
    """Elimina una aplicación y todos sus registros dependientes."""
    db.session.execute(db.text("DELETE FROM clustering_asignaciones WHERE aplicacion_id = :ap_id"), {"ap_id": ap.id})
    Respuesta.query.filter_by(aplicacion_id=ap.id).delete()
    ResultadoDimension.query.filter_by(aplicacion_id=ap.id).delete()
    PerfilVocacional.query.filter_by(aplicacion_id=ap.id).delete()
    db.session.delete(ap)
    db.session.flush()


def _crear_completada(estudiante, config, pesos, periodo_idx, app_ctx):
    """Crea una aplicación completada con respuestas simuladas y perfil calculado."""
    with app_ctx.app_context():
        # Calcular fecha dentro del periodo
        p_inicio = config.fecha_inicio or (datetime.utcnow() - timedelta(days=200 - periodo_idx * 90))
        p_fin    = config.fecha_fin    or (datetime.utcnow() - timedelta(days=170 - periodo_idx * 90))

        delta = max(int((p_fin - p_inicio).total_seconds()), 1)
        offset_seg = random.randint(0, delta - 1)
        fecha_inicio = p_inicio + timedelta(seconds=offset_seg)
        fecha_fin    = fecha_inicio + timedelta(minutes=random.randint(14, 28))

        ap = Aplicacion(
            usuario_id=estudiante.id,
            configuracion_id=config.id,
            estado='completada',
            progreso=100,
            ip_address='127.0.0.1',
            user_agent='FixCompletarPruebas/1.0',
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )
        db.session.add(ap)
        db.session.flush()

        # Generar respuestas
        for dimension in config.instrumento.dimensiones:
            for escala in dimension.escalas:
                area = escala.nombre
                peso = pesos.get(area, 0.5)
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
            print('DEBUG: pesos=', pesos); PsicometricoService.calcular_puntajes_dimension(ap.id)
            perfil = PsicometricoService.generar_perfil(ap.id)
            print(f"      [OK] Periodo {periodo_idx+1} [{fecha_fin.strftime('%Y-%m-%d')}] -> {perfil.perfil_principal}/{perfil.perfil_secundario}")
            return ap
        except Exception as e:
            db.session.rollback()
            print(f"      [ERROR] Error en periodo {periodo_idx+1}: {e}")
            return None


def _tiene_datos_validos(ap):
    """Retorna True si la aplicación completada tiene ResultadoDimension con datos no nulos."""
    resultados = ResultadoDimension.query.filter_by(aplicacion_id=ap.id).all()
    if not resultados:
        return False
    for r in resultados:
        if r.puntaje_normalizado is None:
            return False
    return True


def main():
    app = create_app()

    with app.app_context():
        # Cargar las 3 configuraciones de evolución
        configs = []
        for nombre in NOMBRES_PERIODOS:
            c = ConfiguracionAplicacion.query.filter_by(nombre=nombre).first()
            if not c:
                print(f"ERROR: No se encontró la configuración '{nombre}'.")
                print("Ejecuta primero: python seed_evolucion_masiva.py")
                return
            configs.append(c)
        print(f"[OK] Configuraciones cargadas: {[c.nombre[-20:] for c in configs]}\n")

        # Obtener todos los estudiantes activos
        estudiantes = (
            Usuario.query
            .join(Rol)
            .filter(Rol.nombre == 'estudiante', Usuario.activo == True)
            .order_by(Usuario.id)
            .all()
        )
        print(f"=== {len(estudiantes)} estudiantes encontrados ===\n")

        reparados = 0
        creados   = 0
        ya_ok     = 0

        for orden, estudiante in enumerate(estudiantes):
            patron_idx = orden % len(PATRONES_EVOLUCION)
            patron     = PATRONES_EVOLUCION[patron_idx]
            nombre_est = f"{estudiante.nombres} {estudiante.apellidos}"
            print(f"[STUDENT] [{estudiante.id}] {nombre_est} (patron {patron_idx})")

            for p_idx, config in enumerate(configs):
                # Borrar TODAS las aplicaciones existentes para este par y recrear
                apps_previas = Aplicacion.query.filter_by(
                    usuario_id=estudiante.id,
                    configuracion_id=config.id,
                ).all()

                for ap in apps_previas:
                    _borrar_app(ap)
                if apps_previas:
                    db.session.commit()
                    reparados += 1

                _crear_completada(estudiante, config, patron[p_idx], p_idx, app)
                creados += 1

            print()

        print("=" * 60)
        print(f"[OK] Proceso completado.")
        print(f"  Aplicaciones anteriores borradas: {reparados}")
        print(f"  Aplicaciones nuevas creadas:      {creados}")
        print("=" * 60)


if __name__ == '__main__':
    main()
