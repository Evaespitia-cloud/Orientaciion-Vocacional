"""
Seed script: crea dos instrumentos Holland RIASEC completos y sus configuraciones.
  - Instrumento 1: Prueba de Intereses Vocacionales (Sí/No)
  - Instrumento 2: Prueba de Competencias Vocacionales (Opción múltiple)
  - Dos configuraciones activas (visibles para los estudiantes hoy)

Ejecutar con: python seed_instruments.py
"""

import psycopg2
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv('DATABASE_URL')
if not DB_URL:
    raise RuntimeError('Define DATABASE_URL antes de ejecutar este script.')

# NOTA: El banco de preguntas NO se define aquí.
# La única fuente oficial es ../data/Items Full day.xlsx (30 + 30).

# ──────────────────────────────────────────────────────────────────────────────
# Definiciones antiguas conservadas únicamente como referencia de estructura.
# No se insertan en la base de datos.
# ──────────────────────────────────────────────────────────────────────────────
INTERESES_ITEMS = {
    "Realista": [
        "¿Te gusta trabajar con herramientas, máquinas o equipos técnicos?",
        "¿Disfrutas las actividades físicas o al aire libre?",
        "¿Te interesa reparar o construir cosas con tus manos?",
        "¿Prefieres las actividades prácticas sobre las teóricas?",
        "¿Te gustaría trabajar en ingeniería, mecánica o construcción?",
    ],
    "Investigador": [
        "¿Te gusta resolver problemas complejos mediante el análisis?",
        "¿Disfrutas investigar y descubrir cómo funcionan las cosas?",
        "¿Te interesa realizar experimentos o estudios científicos?",
        "¿Te gusta leer artículos científicos o de divulgación?",
        "¿Disfrutas trabajando con datos, números y estadísticas?",
    ],
    "Artístico": [
        "¿Te gusta expresarte a través del arte, la música o la escritura?",
        "¿Disfrutas diseñando cosas nuevas e innovadoras?",
        "¿Te atrae trabajar en ambientes que valoran la creatividad?",
        "¿Te gusta actuar, cantar, bailar o tocar un instrumento?",
        "¿Prefieres encontrar soluciones originales a los problemas?",
    ],
    "Social": [
        "¿Te satisface ayudar a otras personas a resolver sus problemas?",
        "¿Disfrutas enseñando o capacitando a otros?",
        "¿Te gusta trabajar en equipo y colaborar con compañeros?",
        "¿Te interesa el bienestar emocional y social de las personas?",
        "¿Te gustaría trabajar como consejero, profesor o terapeuta?",
    ],
    "Emprendedor": [
        "¿Te gusta liderar equipos y tomar decisiones importantes?",
        "¿Te interesa crear y administrar tu propio negocio?",
        "¿Disfrutas persuadiendo o convenciendo a otros?",
        "¿Te motiva competir y lograr metas ambiciosas?",
        "¿Te ves dirigiendo un proyecto o empresa en el futuro?",
    ],
    "Convencional": [
        "¿Te gusta organizar información y mantener registros ordenados?",
        "¿Disfrutas siguiendo procedimientos y reglas establecidas?",
        "¿Te sientes cómodo/a trabajando con hojas de cálculo o bases de datos?",
        "¿Prefieres un ambiente de trabajo estructurado y predecible?",
        "¿Te gusta la contabilidad, la administración o el archivo de documentos?",
    ],
}

# ──────────────────────────────────────────────────────────────────────────────
# Ítems de COMPETENCIAS  (opcion_multiple: valor 1 = opción correcta/afín)
# ──────────────────────────────────────────────────────────────────────────────
COMPETENCIAS_ITEMS = {
    "Realista": [
        {
            "texto": "¿Cuál de estas actividades realizarías con mayor habilidad?",
            "opciones": [
                {"texto": "Armar o reparar un equipo electrónico o mecánico", "valor": 1},
                {"texto": "Escribir un ensayo argumentativo detallado", "valor": 0},
                {"texto": "Organizar un evento y coordinar personas", "valor": 0},
            ],
        },
        {
            "texto": "En un proyecto escolar, ¿qué rol preferirías y en qué eres mejor?",
            "opciones": [
                {"texto": "Construir la maqueta, prototipo o parte práctica", "valor": 1},
                {"texto": "Realizar la investigación y redactar el informe", "valor": 0},
                {"texto": "Presentar los resultados frente al público", "valor": 0},
            ],
        },
        {
            "texto": "¿Qué tarea completarías mejor en un trabajo de campo?",
            "opciones": [
                {"texto": "Instalar, ajustar o reparar equipos en el lugar", "valor": 1},
                {"texto": "Analizar los datos recogidos y sacar conclusiones", "valor": 0},
                {"texto": "Coordinar al equipo y asignar responsabilidades", "valor": 0},
            ],
        },
    ],
    "Investigador": [
        {
            "texto": "¿Cómo resolverías un problema desconocido de forma más efectiva?",
            "opciones": [
                {"texto": "Investigando, recopilando datos y analizando resultados", "valor": 1},
                {"texto": "Preguntando a expertos y siguiendo sus indicaciones", "valor": 0},
                {"texto": "Probando soluciones directamente sin planificación previa", "valor": 0},
            ],
        },
        {
            "texto": "¿En qué tipo de lectura o estudio te destacas más?",
            "opciones": [
                {"texto": "Artículos científicos, libros técnicos y documentales", "valor": 1},
                {"texto": "Novelas, obras literarias y textos creativos", "valor": 0},
                {"texto": "Manuales de procedimientos y guías prácticas", "valor": 0},
            ],
        },
        {
            "texto": "¿Qué materia escolar te resulta más fácil y en la que mejor te desempeñas?",
            "opciones": [
                {"texto": "Ciencias, matemáticas o química", "valor": 1},
                {"texto": "Arte, música o literatura", "valor": 0},
                {"texto": "Educación física, manualidades o tecnología básica", "valor": 0},
            ],
        },
    ],
    "Artístico": [
        {
            "texto": "¿Cómo expresas mejor una idea importante o un mensaje?",
            "opciones": [
                {"texto": "Con una pintura, canción, poema o diseño visual", "valor": 1},
                {"texto": "Con un discurso o presentación formal apoyada en datos", "valor": 0},
                {"texto": "Con un informe escrito estructurado y detallado", "valor": 0},
            ],
        },
        {
            "texto": "¿En qué actividad extracurricular te has destacado más?",
            "opciones": [
                {"texto": "Teatro, música, danza, taller de arte o diseño", "valor": 1},
                {"texto": "Club de ciencias, robótica o matemáticas", "valor": 0},
                {"texto": "Voluntariado, liderazgo estudiantil o emprendimiento", "valor": 0},
            ],
        },
        {
            "texto": "¿Qué tipo de trabajo harías con mayor calidad?",
            "opciones": [
                {"texto": "Diseñar logos, crear contenido visual o componer música", "valor": 1},
                {"texto": "Analizar datos financieros y elaborar informes técnicos", "valor": 0},
                {"texto": "Vender, negociar o gestionar un equipo de trabajo", "valor": 0},
            ],
        },
    ],
    "Social": [
        {
            "texto": "¿Qué harías si un compañero enfrenta un problema personal?",
            "opciones": [
                {"texto": "Escucharlo activamente y ayudarlo a encontrar soluciones", "valor": 1},
                {"texto": "Investigar el problema de forma objetiva y presentar datos", "valor": 0},
                {"texto": "Sugerirle que busque a alguien más capacitado para ayudar", "valor": 0},
            ],
        },
        {
            "texto": "¿En qué ambiente de trabajo te sientes más hábil y efectivo/a?",
            "opciones": [
                {"texto": "En un hospital, escuela, ONG o centro comunitario", "valor": 1},
                {"texto": "En un laboratorio, biblioteca o centro de investigación", "valor": 0},
                {"texto": "En una oficina corporativa o sala de juntas empresarial", "valor": 0},
            ],
        },
        {
            "texto": "¿Qué capacidad te reconocen más tus compañeros y profesores?",
            "opciones": [
                {"texto": "Capacidad de escuchar, apoyar y motivar a los demás", "valor": 1},
                {"texto": "Habilidad para analizar y explicar temas complejos", "valor": 0},
                {"texto": "Iniciativa y capacidad de organización de grupos", "valor": 0},
            ],
        },
    ],
    "Emprendedor": [
        {
            "texto": "¿Cómo manejarías más efectivamente un conflicto en un grupo?",
            "opciones": [
                {"texto": "Tomando el liderazgo, proponiendo soluciones y decidiendo", "valor": 1},
                {"texto": "Mediando para que cada persona exprese su punto de vista", "valor": 0},
                {"texto": "Analizando objetivamente cada argumento antes de actuar", "valor": 0},
            ],
        },
        {
            "texto": "¿Qué habilidad crees que te daría mayor éxito profesional?",
            "opciones": [
                {"texto": "Persuasión, negociación y visión de negocios", "valor": 1},
                {"texto": "Empatía, comunicación asertiva y trabajo en equipo", "valor": 0},
                {"texto": "Precisión, organización y manejo detallado de datos", "valor": 0},
            ],
        },
        {
            "texto": "Si tuvieras que liderar un proyecto desde cero, ¿qué harías primero?",
            "opciones": [
                {"texto": "Definir el plan de negocio, el mercado y la estrategia de crecimiento", "valor": 1},
                {"texto": "Investigar a fondo el tema y hacer un diagnóstico completo", "valor": 0},
                {"texto": "Organizar el equipo, asignar tareas y crear un cronograma detallado", "valor": 0},
            ],
        },
    ],
    "Convencional": [
        {
            "texto": "¿Cómo organizarías de forma más eficiente un evento escolar?",
            "opciones": [
                {"texto": "Creando listas detalladas, cronogramas y presupuestos", "valor": 1},
                {"texto": "Motivando al equipo con ideas creativas y entusiasmo", "valor": 0},
                {"texto": "Delegando tareas según las habilidades de cada persona", "valor": 0},
            ],
        },
        {
            "texto": "¿Qué tarea académica realizas con mayor facilidad y precisión?",
            "opciones": [
                {"texto": "Clasificar, organizar y sistematizar documentos o datos", "valor": 1},
                {"texto": "Crear proyectos artísticos, visuales o literarios", "valor": 0},
                {"texto": "Liderar debates, presentaciones o actividades grupales", "valor": 0},
            ],
        },
        {
            "texto": "¿Qué cualidad te describe mejor en tu forma de trabajar?",
            "opciones": [
                {"texto": "Organizado/a, metódico/a y muy orientado/a al detalle", "valor": 1},
                {"texto": "Creativo/a, espontáneo/a y con pensamiento original", "valor": 0},
                {"texto": "Dinámico/a, sociable y orientado/a a las relaciones humanas", "valor": 0},
            ],
        },
    ],
}

AREAS = [
    ("Realista",     "Actividades prácticas, mecánicas y al aire libre"),
    ("Investigador", "Actividades científicas, analíticas e investigativas"),
    ("Artístico",    "Actividades creativas, artísticas y de expresión libre"),
    ("Social",       "Actividades de ayuda, enseñanza y servicio social"),
    ("Emprendedor",  "Actividades de liderazgo, persuasión y negocios"),
    ("Convencional", "Actividades organizativas, de datos y procedimientos"),
]


def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # ── 1. Obtener ID del usuario administrador (ti) ──────────────────────────
    cur.execute("""
        SELECT u.id FROM usuarios u
        JOIN roles r ON u.rol_id = r.id
        WHERE r.nombre = 'ti' AND u.activo = TRUE
        LIMIT 1
    """)
    row = cur.fetchone()
    admin_id = row[0] if row else None
    print(f"Admin ID: {admin_id}")

    # ── 2. Limpiar datos anteriores de instrumentos ───────────────────────────
    print("\nLimpiando datos existentes de instrumentos...")
    for tabla in ("respuestas", "resultados_dimension", "perfiles_vocacionales",
                  "reportes", "aplicaciones", "configuraciones_aplicacion",
                  "items", "escalas", "dimensiones", "instrumentos"):
        cur.execute(f"DELETE FROM {tabla}")
        print(f"  Tabla {tabla}: limpia")

    # ── 3. Crear instrumentos ─────────────────────────────────────────────────
    print("\nCreando instrumentos Holland RIASEC...")

    cur.execute("""
        INSERT INTO instrumentos (nombre, descripcion, version, activo, creado_por)
        VALUES (%s, %s, '1.0', TRUE, %s) RETURNING id
    """, (
        "Prueba de Intereses Vocacionales Holland",
        ("Inventario de intereses vocacionales basado en la teoría RIASEC de John Holland. "
         "Evalúa las preferencias del estudiante en seis áreas: Realista (R), Investigador (I), "
         "Artístico (A), Social (S), Emprendedor (E) y Convencional (C). "
         "Responde Sí o No a cada afirmación según tus gustos personales."),
        admin_id,
    ))
    inst1_id = cur.fetchone()[0]

    cur.execute("""
        INSERT INTO instrumentos (nombre, descripcion, version, activo, creado_por)
        VALUES (%s, %s, '1.0', TRUE, %s) RETURNING id
    """, (
        "Prueba de Competencias Vocacionales Holland",
        ("Inventario de competencias y habilidades vocacionales basado en la teoría RIASEC de John Holland. "
         "Evalúa las capacidades percibidas del estudiante en seis áreas. "
         "Para cada pregunta, elige la opción que mejor describa lo que harías o en qué te destacas más."),
        admin_id,
    ))
    inst2_id = cur.fetchone()[0]

    print(f"  Instrumento 1 (Intereses)    id={inst1_id}")
    print(f"  Instrumento 2 (Competencias) id={inst2_id}")

    # ── 4. Crear dimensiones ──────────────────────────────────────────────────
    cur.execute("""
        INSERT INTO dimensiones (instrumento_id, nombre, descripcion, peso, orden)
        VALUES (%s, %s, %s, 1.0, 1) RETURNING id
    """, (
        inst1_id,
        "Intereses Vocacionales",
        "Evalúa los intereses y preferencias vocacionales en las seis áreas Holland RIASEC "
        "mediante elección forzada (Sí/No).",
    ))
    dim1_id = cur.fetchone()[0]

    cur.execute("""
        INSERT INTO dimensiones (instrumento_id, nombre, descripcion, peso, orden)
        VALUES (%s, %s, %s, 1.0, 1) RETURNING id
    """, (
        inst2_id,
        "Competencias Vocacionales",
        "Evalúa las competencias y habilidades vocacionales percibidas en las seis áreas Holland RIASEC "
        "mediante preguntas de opción múltiple.",
    ))
    dim2_id = cur.fetchone()[0]

    print(f"  Dimensión 1 (Intereses)    id={dim1_id}")
    print(f"  Dimensión 2 (Competencias) id={dim2_id}")

    # ── 5. Crear únicamente las escalas ─────────────────────────────────────
    # Los ítems se sincronizan después desde el Excel oficial 30 + 30.
    print("\nCreando escalas RIASEC...")
    for orden, (area, desc) in enumerate(AREAS, 1):
        cur.execute("""
            INSERT INTO escalas (dimension_id, nombre, descripcion, valor_minimo, valor_maximo, orden)
            VALUES (%s, %s, %s, 0, 1, %s)
        """, (dim1_id, area, desc, orden))
        cur.execute("""
            INSERT INTO escalas (dimension_id, nombre, descripcion, valor_minimo, valor_maximo, orden)
            VALUES (%s, %s, %s, 1, 4, %s)
        """, (dim2_id, area, desc, orden))
        print(f"  Escalas creadas: {area}")

    # ── 6. Crear configuraciones de aplicación (activas desde hoy) ────────────
    print("\nCreando configuraciones de aplicación...")

    ahora = datetime.utcnow()
    fecha_fin = ahora + timedelta(days=180)

    cur.execute("""
        INSERT INTO configuraciones_aplicacion
            (instrumento_id, nombre, descripcion, fecha_inicio, fecha_fin,
             obligatoria, activa, creado_por)
        VALUES (%s, %s, %s, %s, %s, TRUE, TRUE, %s) RETURNING id
    """, (
        inst1_id,
        "Prueba de Intereses Holland — Semestre 2025-I",
        ("Inventario de intereses vocacionales RIASEC. "
         "Indica con Sí o No si cada afirmación describe tus preferencias. "
         "No hay respuestas correctas ni incorrectas — responde con sinceridad."),
        ahora,
        fecha_fin,
        admin_id,
    ))
    config1_id = cur.fetchone()[0]

    cur.execute("""
        INSERT INTO configuraciones_aplicacion
            (instrumento_id, nombre, descripcion, fecha_inicio, fecha_fin,
             obligatoria, activa, creado_por)
        VALUES (%s, %s, %s, %s, %s, TRUE, TRUE, %s) RETURNING id
    """, (
        inst2_id,
        "Prueba de Competencias Holland — Semestre 2025-I",
        ("Inventario de competencias vocacionales RIASEC. "
         "Para cada pregunta, elige la opción que mejor describa lo que harías "
         "o en qué te destacas más. No hay respuestas correctas ni incorrectas."),
        ahora,
        fecha_fin,
        admin_id,
    ))
    config2_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    # Sincronizar las 60 preguntas oficiales (30 Intereses + 30 Competencias).
    import sys
    from pathlib import Path
    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root))
    from importar_banco_cliente import cargar_banco_desde_excel, importar_en_bd
    excel = project_root / 'data' / 'Items Full day.xlsx'
    intereses, competencias = cargar_banco_desde_excel(excel)
    importar_en_bd(intereses, competencias, '3.0')
    total_int = len(intereses)
    total_comp = len(competencias)

    print(f"\n{'=' * 55}")
    print("INSTRUMENTOS CREADOS EXITOSAMENTE")
    print(f"{'=' * 55}")
    print(f"  Instrumento 1 — Intereses    : id={inst1_id}, {total_int} ítems oficiales")
    print(f"  Instrumento 2 — Competencias : id={inst2_id}, {total_comp} ítems oficiales")
    print(f"  Configuración 1              : id={config1_id}")
    print(f"  Configuración 2              : id={config2_id}")
    print(f"  Válidas hasta                : {fecha_fin.date()}")
    print(f"\n  Los estudiantes verán AMBAS pruebas en su panel de inicio.")
    print(f"{'=' * 55}")


if __name__ == "__main__":
    main()
