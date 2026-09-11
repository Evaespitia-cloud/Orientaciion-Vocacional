
# LEGACY / NO USAR PARA EL BANCO ACTUAL.
# El banco oficial vigente es data/Items Full day.xlsx (30 Intereses + 30 Competencias).
# Use importar_banco_cliente.py.
# -*- coding: utf-8 -*-
"""Compatibilidad histórica para importar el banco completo del cliente.

La implementación vigente está en ``importar_banco_cliente.py`` y carga las
60 fichas de intereses y los 64 ítems de competencias. Este archivo conserva
su nombre para no romper instrucciones antiguas, pero delega la ejecución al
importador validado y ya no carga el banco sintético anterior.
"""
import sys
import os

if __name__ == '__main__':
        from importar_banco_cliente import main
        raise SystemExit(main())

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app import create_app  # noqa: E402

app = create_app()

with app.app_context():
    from backend.app.extensions import db
    from backend.app.models.instrumento import Instrumento, Dimension, Escala, Item
    from sqlalchemy import text

    # 1. Asegurar columnas nuevas en items (codigo, contexto, version)
    db.session.execute(text("ALTER TABLE items ADD COLUMN IF NOT EXISTS codigo VARCHAR(20)"))
    db.session.execute(text("ALTER TABLE items ADD COLUMN IF NOT EXISTS contexto TEXT"))
    db.session.execute(text("ALTER TABLE items ADD COLUMN IF NOT EXISTS version VARCHAR(10) DEFAULT '1.0'"))
    db.session.commit()

    instrumento = Instrumento.query.first()
    if not instrumento:
        raise SystemExit('No hay ningún instrumento creado. Ejecuta primero init_db.sql / migrate_holland.sql.')

    # En este sistema Intereses y Competencias son instrumentos separados (cada uno
    # con una única dimensión), no un instrumento con dos dimensiones.
    dim_intereses = Dimension.query.filter(Dimension.nombre.ilike('%interes%')).first()
    dim_competencias = Dimension.query.filter(Dimension.nombre.ilike('%competencia%')).first()
    if not dim_intereses or not dim_competencias:
        raise SystemExit('No se encontraron las dimensiones "Intereses" y "Competencias".')

    escalas_intereses = {e.nombre: e for e in dim_intereses.escalas}
    escalas_competencias = {e.nombre: e for e in dim_competencias.escalas}

    # 2. Borrar los ítems actuales de ambas dimensiones (se reconstruye el banco completo)
    for escala in list(escalas_intereses.values()) + list(escalas_competencias.values()):
        Item.query.filter_by(escala_id=escala.id).delete()
    db.session.commit()

    # Ajustar rango de puntuación de las escalas al nuevo diseño
    for escala in escalas_intereses.values():
        escala.valor_minimo, escala.valor_maximo = 0, 1
    for escala in escalas_competencias.values():
        escala.valor_minimo, escala.valor_maximo = 1, 4
    db.session.commit()

    # =====================================================================
    # 3. ESCALA DE INTERESES — 30 ítems de comparación binaria (15 pares x 2)
    # =====================================================================
    # Enunciados declarativos por campo RIASEC (reutilizan/adaptan el banco previo)
    R = [
        'Trabajar con herramientas, máquinas o equipos.',
        'Realizar actividades físicas o al aire libre.',
        'Reparar o construir cosas con las manos.',
        'Hacer actividades prácticas antes que teóricas.',
        'Operar maquinaria o vehículos.',
    ]
    I = [
        'Resolver problemas complejos mediante el análisis.',
        'Investigar y descubrir cómo funcionan las cosas.',
        'Realizar experimentos o estudios científicos.',
        'Leer artículos científicos o documentales.',
        'Trabajar con datos, números y estadísticas.',
    ]
    A = [
        'Expresarme a través del arte, la música o la escritura.',
        'Diseñar cosas nuevas e innovadoras.',
        'Trabajar en ambientes que valoran la creatividad.',
        'Actuar, cantar, bailar o tocar un instrumento.',
        'Encontrar soluciones originales a los problemas.',
    ]
    S = [
        'Ayudar a otras personas a resolver sus problemas.',
        'Enseñar o capacitar a otros.',
        'Trabajar en equipo y colaborar con otros.',
        'Apoyar el bienestar emocional y social de las personas.',
        'Trabajar como consejero, profesor o terapeuta.',
    ]
    E = [
        'Liderar equipos y tomar decisiones.',
        'Crear y administrar mi propio negocio.',
        'Persuadir o convencer a otros.',
        'Competir y lograr metas ambiciosas.',
        'Dirigir un proyecto o empresa en el futuro.',
    ]
    C = [
        'Organizar información y mantener registros ordenados.',
        'Seguir procedimientos y reglas establecidas.',
        'Trabajar con hojas de cálculo y bases de datos.',
        'Trabajar en un ambiente estructurado y predecible.',
        'Dedicarme a la contabilidad, la administración o el archivo.',
    ]

    BANCOS = {'Realista': R, 'Investigador': I, 'Artístico': A, 'Social': S, 'Emprendedor': E, 'Convencional': C}

    # 15 pares RIASEC, en el orden definido por los lineamientos del cliente.
    PARES = [
        ('Realista', 'Investigador'), ('Realista', 'Artístico'), ('Realista', 'Social'),
        ('Realista', 'Emprendedor'), ('Realista', 'Convencional'),
        ('Investigador', 'Artístico'), ('Investigador', 'Social'), ('Investigador', 'Emprendedor'),
        ('Investigador', 'Convencional'),
        ('Artístico', 'Social'), ('Artístico', 'Emprendedor'), ('Artístico', 'Convencional'),
        ('Social', 'Emprendedor'), ('Social', 'Convencional'),
        ('Emprendedor', 'Convencional'),
    ]

    PREFIJO = {'Realista': 'REA', 'Investigador': 'INV', 'Artístico': 'ART', 'Social': 'SOC', 'Emprendedor': 'EMP', 'Convencional': 'CON'}

    # Índice cíclico (0-4) de qué frase del banco de cada campo se usa en su k-ésima participación
    contador_area = {area: 0 for area in BANCOS}
    orden_item = 0

    for par_idx, (area_a, area_b) in enumerate(PARES, start=1):
        k_a = contador_area[area_a]
        k_b = contador_area[area_b]
        contador_area[area_a] += 1
        contador_area[area_b] += 1

        banco_a, banco_b = BANCOS[area_a], BANCOS[area_b]
        # 2 ítems por par, usando frases distintas y cíclicas del banco de cada campo
        parejas = [
            (banco_a[k_a % 5], banco_b[k_b % 5]),
            (banco_a[(k_a + 1) % 5], banco_b[(k_b + 1) % 5]),
        ]

        for item_num, (texto_a, texto_b) in enumerate(parejas, start=1):
            orden_item += 1
            codigo = f"INT-{PREFIJO[area_a]}-{PREFIJO[area_b]}-{item_num:02d}"
            # Agrupación administrativa balanceada: el 1er ítem del par se agrupa bajo
            # el campo A y el 2do bajo el campo B, así cada campo termina con 5 ítems
            # (30 ítems / 6 campos), en vez de agrupar siempre bajo el campo A.
            escala_destino = escalas_intereses[area_a] if item_num == 1 else escalas_intereses[area_b]
            item = Item(
                escala_id=escala_destino.id,
                codigo=codigo,
                texto='¿Cuál de estas dos actividades disfrutarías más?',
                contexto=None,
                tipo='comparacion_binaria',
                opciones={
                    'opcion_a': {'campo': area_a, 'texto': texto_a},
                    'opcion_b': {'campo': area_b, 'texto': texto_b},
                },
                obligatorio=True,
                orden=orden_item,
                version='1.0',
            )
            db.session.add(item)

    db.session.commit()
    print(f'Intereses: {orden_item} ítems de comparación binaria creados (15 pares x 2).')

    # =====================================================================
    # 4. ESCALA DE COMPETENCIAS — 30 ítems de juicio situacional (5 por campo)
    # =====================================================================
    def opciones_juicio(a_texto, b_texto, c_texto, d_texto, a_pts, b_pts, c_pts, d_pts):
        return {
            'opciones': [
                {'letra': 'A', 'texto': a_texto, 'puntaje': a_pts},
                {'letra': 'B', 'texto': b_texto, 'puntaje': b_pts},
                {'letra': 'C', 'texto': c_texto, 'puntaje': c_pts},
                {'letra': 'D', 'texto': d_texto, 'puntaje': d_pts},
            ]
        }

    # Cada tupla: (codigo, contexto, enunciado, opciones dict)
    ITEMS_COMPETENCIAS = {
        'Realista': [
            ('REA-01', 'En tu clase de tecnología, el equipo con el que debes hacer una práctica deja de funcionar justo antes de la entrega.',
             opciones_juicio(
                 'Revisar el equipo pieza por pieza para identificar la falla antes de pedir ayuda.',
                 'Avisar al profesor de inmediato y esperar a que lo repare otra persona.',
                 'Dejar la práctica pendiente y entregarla incompleta.',
                 'Pedir a un compañero que lo revise mientras tú observas.',
                 4, 2, 1, 3)),
            ('REA-02', 'Durante una salida de campo, el vehículo del grupo se queda varado en un camino destapado.',
             opciones_juicio(
                 'Buscar ayuda inmediatamente sin intentar nada más.',
                 'Revisar con calma qué pudo haber fallado y proponer una solución práctica al grupo.',
                 'Sugerir empujar el vehículo sin evaluar la causa del problema.',
                 'Esperar sin hacer nada a que alguien más resuelva el problema.',
                 2, 4, 3, 1)),
            ('REA-03', 'Te asignan armar una maqueta física para un proyecto escolar en equipo.',
             opciones_juicio(
                 'No participar activamente y esperar que otros lo resuelvan.',
                 'Ayudar solo si alguien te lo pide directamente.',
                 'Proponerte para la parte de construcción y ensamblaje de materiales.',
                 'Preferir encargarte solo de la parte escrita del proyecto.',
                 1, 3, 4, 2)),
            ('REA-04', 'En el laboratorio del colegio, una máquina sencilla no enciende y el profesor pide ayuda.',
             opciones_juicio(
                 'Sugerir cambiar de máquina sin revisar la causa.',
                 'Decir que no sabes nada de eso y alejarte.',
                 'Preguntar a otro compañero qué haría él, sin intentarlo tú mismo.',
                 'Ofrecerte a revisar cables y conexiones antes de descartar la máquina.',
                 3, 1, 2, 4)),
            ('REA-05', 'Un familiar te pide ayuda para reparar un objeto dañado en casa (una silla, una puerta, etc.).',
             opciones_juicio(
                 'Aceptar y buscar la manera práctica de arreglarlo con las herramientas disponibles.',
                 'Ayudar solo a sostener mientras otro lo repara.',
                 'Decir que no te interesa y evitar la tarea.',
                 'Ofrecer buscar un video tutorial y luego intentarlo.',
                 4, 2, 1, 3)),
        ],
        'Investigador': [
            ('INV-01', 'En una tarea de ciencias, obtienes un resultado inesperado en un experimento sencillo.',
             opciones_juicio(
                 'Repetir el experimento y anotar posibles causas del resultado.',
                 'Preguntar a un compañero la respuesta correcta sin analizar por qué pasó.',
                 'Ignorar el resultado y entregar lo que esperabas obtener.',
                 'Anotar el resultado extraño pero sin investigar más.',
                 4, 2, 1, 3)),
            ('INV-02', 'Te piden explicar por qué ocurre un fenómeno cotidiano (por ejemplo, por qué llueve).',
             opciones_juicio(
                 'Dar una respuesta rápida sin verificarla.',
                 'Buscar información confiable y comparar varias fuentes antes de responder.',
                 'Preguntar la opinión de otros sin revisar los datos tú mismo.',
                 'Copiar la primera respuesta que encuentres en internet.',
                 2, 4, 3, 1)),
            ('INV-03', 'En un trabajo grupal deben resolver un problema matemático complejo.',
             opciones_juicio(
                 'Esperar que otro del grupo lo resuelva primero.',
                 'Seguir el procedimiento de un compañero sin verificarlo.',
                 'Proponer analizar el problema por partes antes de intentar resolverlo.',
                 'Intentar adivinar la respuesta sin analizar el procedimiento.',
                 1, 3, 4, 2)),
            ('INV-04', 'Encuentras una noticia con datos estadísticos que parecen contradictorios.',
             opciones_juicio(
                 'Leer solo el titular y asumir que es correcto.',
                 'Compartirla de inmediato sin revisar la fuente.',
                 'Preguntar la opinión de otros sin revisar los datos tú mismo.',
                 'Verificar la fuente y los datos antes de sacar una conclusión.',
                 3, 1, 2, 4)),
            ('INV-05', 'Un profesor propone un reto de investigación libre para el bimestre.',
             opciones_juicio(
                 'Elegir un tema y planear cómo investigarlo con orden y análisis.',
                 'Elegir el tema más fácil sin pensar en el proceso.',
                 'Copiar un trabajo de investigación ya hecho por alguien más.',
                 'Elegir un tema interesante pero sin plan claro de investigación.',
                 4, 2, 1, 3)),
        ],
        'Artístico': [
            ('ART-01', 'Debes presentar un trabajo escolar y el profesor permite elegir el formato de entrega.',
             opciones_juicio(
                 'Elegir una forma creativa y original de mostrar la información (video, arte, diseño).',
                 'Elegir el formato más simple sin pensar en cómo comunicarlo mejor.',
                 'Copiar el formato que usó un compañero el año anterior.',
                 'Elegir un formato distinto solo porque otros lo eligieron.',
                 4, 2, 1, 3)),
            ('ART-02', 'En una actividad grupal, deben decorar un espacio para un evento del colegio.',
             opciones_juicio(
                 'Aportar una idea solo si alguien más la pide directamente.',
                 'Proponer ideas nuevas y ayudar a diseñar la decoración.',
                 'Seguir instrucciones exactas sin aportar ideas propias.',
                 'No participar en la parte creativa del proyecto.',
                 2, 4, 3, 1)),
            ('ART-03', 'Tienes que expresar una opinión personal importante frente al curso.',
             opciones_juicio(
                 'Evitar expresarla por miedo a equivocarte.',
                 'Explicarla de forma clara pero sin buscar una forma distinta de contarla.',
                 'Prepararla usando una forma creativa de comunicarla (metáfora, imagen, ejemplo original).',
                 'Leerla de un papel sin ninguna variación personal.',
                 1, 3, 4, 2)),
            ('ART-04', 'El colegio organiza un concurso de talentos y puedes participar si quieres.',
             opciones_juicio(
                 'Participar repitiendo algo que ya viste hacer a otra persona.',
                 'No participar aunque te gustaría.',
                 'Participar solo si un amigo te acompaña.',
                 'Inscribirte y preparar una presentación propia y original.',
                 3, 1, 2, 4)),
            ('ART-05', 'Un compañero te pide ayuda para hacer más atractivo un cartel o afiche escolar.',
             opciones_juicio(
                 'Ayudarlo proponiendo un diseño distinto y llamativo.',
                 'Ayudarlo solo a escribir el texto, sin opinar del diseño.',
                 'Decir que no sabes de diseño y no ayudar.',
                 'Sugerir copiar un diseño que ya existe.',
                 4, 2, 1, 3)),
        ],
        'Social': [
            ('SOC-01', 'Un compañero te dice que últimamente le cuesta concentrarse, se siente desmotivado y tiene dudas sobre continuar en una actividad del colegio.',
             opciones_juicio(
                 'Darle un consejo breve para que organice mejor su tiempo y continúe con la actividad.',
                 'Escuchar lo que plantea, explorar qué le preocupa principalmente y responder con respeto antes de orientar una acción.',
                 'Comparar su situación con casos parecidos y sugerirle que espere a sentirse mejor.',
                 'Preguntarle qué ha intentado hacer y acompañarlo a identificar una primera acción de apoyo.',
                 2, 4, 1, 3)),
            ('SOC-02', 'Un estudiante nuevo llega al salón y no conoce a nadie durante el descanso.',
             opciones_juicio(
                 'Saludarlo de lejos sin acercarte más.',
                 'Acercarte, presentarte y ayudarlo a integrarse con el grupo.',
                 'Pedirle a otro compañero que se encargue de acercarse a él.',
                 'No hacer nada porque no es tu responsabilidad.',
                 2, 4, 3, 1)),
            ('SOC-03', 'Dos compañeros están discutiendo fuerte por un malentendido en un trabajo grupal.',
             opciones_juicio(
                 'Ignorar la situación y seguir con lo tuyo.',
                 'Comentarles que se calmen sin ayudar más a resolver el conflicto.',
                 'Intervenir con calma para ayudarlos a escucharse y entender el malentendido.',
                 'Tomar partido por uno de los dos sin escuchar al otro.',
                 1, 3, 4, 2)),
            ('SOC-04', 'Un amigo te cuenta que está pasando por un problema familiar difícil.',
             opciones_juicio(
                 'Escucharlo brevemente y luego seguir con tus actividades.',
                 'Decirle que no le des tanta importancia al problema.',
                 'Cambiar el tema para que no se sienta incómodo.',
                 'Escucharlo con atención y acompañarlo, sin minimizar lo que siente.',
                 3, 1, 2, 4)),
            ('SOC-05', 'El profesor pide voluntarios para explicarle un tema a los compañeros que tienen dificultades.',
             opciones_juicio(
                 'Ofrecerte a explicar el tema con paciencia hasta que lo entiendan.',
                 'Ofrecerte solo si te dan algo a cambio.',
                 'No ofrecerte porque prefieres no involucrarte.',
                 'Ofrecerte pero explicarlo de forma apresurada.',
                 4, 2, 1, 3)),
        ],
        'Emprendedor': [
            ('EMP-01', 'Tu curso debe organizar una actividad para recaudar fondos y nadie ha tomado la iniciativa.',
             opciones_juicio(
                 'Proponer una idea concreta y organizar al grupo para llevarla a cabo.',
                 'Esperar a que otro proponga algo primero.',
                 'No participar en la organización de la actividad.',
                 'Apoyar la idea de otro sin aportar nada propio.',
                 4, 2, 1, 3)),
            ('EMP-02', 'En un trabajo grupal hay desacuerdo sobre qué estrategia seguir para cumplir el objetivo.',
             opciones_juicio(
                 'Dejar que el grupo decida sin dar tu opinión.',
                 'Proponer una estrategia clara y motivar al equipo para seguirla.',
                 'Apoyar la idea con más votos sin analizarla.',
                 'Insistir en tu idea sin escuchar las demás propuestas.',
                 2, 4, 3, 1)),
            ('EMP-03', 'Se presenta la oportunidad de liderar un proyecto escolar nuevo.',
             opciones_juicio(
                 'No postularte por miedo a la responsabilidad.',
                 'Postularte pero sin un plan definido.',
                 'Postularte con seguridad y proponer un plan para desarrollarlo.',
                 'Postularte solo si te lo piden directamente.',
                 1, 3, 4, 2)),
            ('EMP-04', 'Un compañero rechaza tu idea para un proyecto frente al grupo.',
             opciones_juicio(
                 'Insistir en tu idea sin explicar por qué es mejor.',
                 'Molestarte y dejar de participar en el proyecto.',
                 'Aceptar el rechazo sin dar más argumentos.',
                 'Explicar con argumentos por qué tu idea puede funcionar y buscar puntos en común.',
                 3, 1, 2, 4)),
            ('EMP-05', 'Tienes la posibilidad de crear un pequeño emprendimiento escolar (venta de algo, servicio, etc.).',
             opciones_juicio(
                 'Planear el emprendimiento identificando qué necesitas y cómo ofrecerlo.',
                 'Intentarlo sin ningún plan ni organización.',
                 'No intentarlo porque prefieres no arriesgarte.',
                 'Intentarlo copiando exactamente la idea de otra persona.',
                 4, 2, 1, 3)),
        ],
        'Convencional': [
            ('CON-01', 'Te encargan organizar los documentos y materiales de un proyecto grupal grande.',
             opciones_juicio(
                 'Crear un sistema claro de carpetas y registros para mantener todo ordenado.',
                 'Organizar solo una parte y dejar el resto a otros.',
                 'Guardar todo junto sin ningún orden específico.',
                 'Pedir a alguien más que se encargue del orden.',
                 4, 2, 1, 3)),
            ('CON-02', 'El profesor pide llevar un registro detallado de las actividades realizadas durante el bimestre.',
             opciones_juicio(
                 'Hacer el registro solo al final, de memoria.',
                 'Llevar el registro completo y actualizado desde el inicio.',
                 'Registrar algunas actividades pero no todas.',
                 'No llevar ningún registro.',
                 2, 4, 3, 1)),
            ('CON-03', 'Debes seguir un instructivo con pasos específicos para completar una tarea.',
             opciones_juicio(
                 'Ignorar el instructivo y hacerlo como prefieras.',
                 'Seguir el instructivo a medias y completar el resto a tu manera.',
                 'Seguir cada paso con cuidado y verificar que esté correcto.',
                 'Seguirlo rápido sin revisar si lo hiciste bien.',
                 1, 3, 4, 2)),
            ('CON-04', 'Te piden clasificar y ordenar una gran cantidad de información para un informe.',
             opciones_juicio(
                 'Organizar solo la parte que te parece más importante.',
                 'Entregar la información desordenada tal como la recibiste.',
                 'Empezar a redactar sin organizar antes la información.',
                 'Organizarla por categorías claras antes de empezar a redactar.',
                 3, 1, 2, 4)),
            ('CON-05', 'Formas parte de un equipo que debe cumplir un cronograma estricto de entregas.',
             opciones_juicio(
                 'Llevar control de fechas y avisar al equipo si algo se está retrasando.',
                 'Confiar en que alguien más llevará el control del tiempo.',
                 'No prestar atención al cronograma.',
                 'Revisar el cronograma solo cerca de la fecha de entrega.',
                 4, 2, 1, 3)),
        ],
    }

    texto_enunciado = 'Ante esta situación, la actuación más adecuada sería'
    orden_item = 0
    total_competencias = 0
    for area, items in ITEMS_COMPETENCIAS.items():
        escala = escalas_competencias[area]
        for codigo, contexto, opciones in items:
            orden_item += 1
            item = Item(
                escala_id=escala.id,
                codigo=codigo,
                texto=texto_enunciado,
                contexto=contexto,
                tipo='juicio_situacional',
                opciones=opciones,
                obligatorio=True,
                orden=orden_item,
                version='1.0',
            )
            db.session.add(item)
            total_competencias += 1

    db.session.commit()
    print(f'Competencias: {total_competencias} ítems de juicio situacional creados (5 por campo x 6 campos).')

    # =====================================================================
    # 5. Campo demográfico "grupo" (requerido por el registro mínimo del estudiante)
    # =====================================================================
    from backend.app.models.demografico import CampoDemografico

    if not CampoDemografico.query.filter_by(nombre='grupo').first():
        max_orden = db.session.query(db.func.max(CampoDemografico.orden)).scalar() or 0
        db.session.add(CampoDemografico(
            nombre='grupo', etiqueta='Grupo o Curso', tipo_campo='texto',
            obligatorio=False, orden=max_orden + 1,
        ))
        db.session.commit()
        print('Campo demográfico "grupo" creado.')

    print('Migración completada.')
