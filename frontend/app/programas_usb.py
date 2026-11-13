"""Pregrados de la USB Medellín y cuáles se recomiendan según el perfil RIASEC.

Única fuente para la página de resultados y el mapa vocacional. No se calcula
ningún porcentaje de afinidad por programa: no hay una fuente que respalde un
perfil RIASEC numérico para cada pregrado. Se recomienda por campo, con la misma
lista que usa el backend (PROGRAMAS_POR_PERFIL en psicometrico_service.py).
"""

import re

URL_BASE = 'https://usbmed.edu.co/programas/pregrados/'
AREAS = ('Realista', 'Investigador', 'Artístico', 'Social', 'Emprendedor', 'Convencional')

# n: nombre, f: facultad, u: ruta en usbmed.edu.co, d: descripción
PROGRAMAS = [
    {'n': 'Licenciatura en Educación Física y Deporte', 'f': 'Educación', 'u': 'licenciatura-en-educacion-fisica-y-deporte', 'd': 'Formación de docentes y gestores del deporte, la educación física y la promoción de la salud.'},
    {'n': 'Tecnología en Entrenamiento Deportivo', 'f': 'Educación', 'u': 'tecnologia-en-entrenamiento-deportivo', 'd': 'Diseño, aplicación y evaluación de planes de entrenamiento deportivo.'},
    {'n': 'Licenciatura en Educación Infantil', 'f': 'Educación', 'u': 'licenciatura-en-educacion-infantil', 'd': 'Acompañamiento del desarrollo integral de niñas y niños en la primera infancia.'},
    {'n': 'Administración de Negocios', 'f': 'Ciencias Empresariales', 'u': 'administracion-de-negocios', 'd': 'Dirección y transformación de organizaciones, con enfoque en emprendimiento e innovación.'},
    {'n': 'Contaduría Pública', 'f': 'Ciencias Empresariales', 'u': 'contaduria-publica', 'd': 'Gestión de la información financiera y contable de las organizaciones.'},
    {'n': 'Negocios Internacionales', 'f': 'Ciencias Empresariales', 'u': 'negocios-internacionales', 'd': 'Internacionalización de empresas y búsqueda de oportunidades en mercados globales.'},
    {'n': 'Arquitectura', 'f': 'Artes Integradas', 'u': 'arquitectura', 'd': 'Diseño y gestión de proyectos arquitectónicos y del espacio habitable.'},
    {'n': 'Diseño de Modas', 'f': 'Artes Integradas', 'u': 'diseno-de-modas', 'd': 'Ideación, diseño y producción de colecciones y líneas de ropa.'},
    {'n': 'Diseño Industrial', 'f': 'Artes Integradas', 'u': 'diseno-industrial', 'd': 'Creación de productos que mejoran el entorno y el bienestar de las personas.'},
    {'n': 'Creación de Contenidos Digitales', 'f': 'Ingenierías', 'u': 'creacion-de-contenidos-digitales', 'd': 'Producción de contenido digital para redes, marcas y medios.'},
    {'n': 'Ingeniería Ambiental', 'f': 'Ingenierías', 'u': 'ingenieria-ambiental', 'd': 'Soluciones técnicas para el desarrollo sostenible y el cuidado del ambiente.'},
    {'n': 'Ingeniería de Datos y Software', 'f': 'Ingenierías', 'u': 'ingenieria-de-datos-y-software', 'd': 'Desarrollo de software y gestión de datos para la industria.'},
    {'n': 'Ingeniería de Sistemas Cibernéticos', 'f': 'Ingenierías', 'u': 'ingenieria-de-sistemas-ciberneticos', 'd': 'Inteligencia artificial, robótica e internet de las cosas.'},
    {'n': 'Ingeniería de Sonido', 'f': 'Ingenierías', 'u': 'ingenieria-de-sonido', 'd': 'Acústica, producción musical y sonido para medios audiovisuales.'},
    {'n': 'Ingeniería Industrial', 'f': 'Ingenierías', 'u': 'ingenieria-industrial', 'd': 'Mejora de procesos, producción, logística y gestión del talento.'},
    {'n': 'Ingeniería Multimedia', 'f': 'Ingenierías', 'u': 'ingenieria-multimedia', 'd': 'Animación, videojuegos, realidad virtual y aumentada, y medios audiovisuales.'},
    {'n': 'Derecho', 'f': 'Derecho', 'u': 'derecho', 'd': 'Formación de abogados con énfasis en la justicia social.'},
    {'n': 'Psicología', 'f': 'Psicología', 'u': 'psicologia', 'd': 'Comprensión del comportamiento humano y acompañamiento a personas y grupos.'},
]

# Copia de PROGRAMAS_POR_PERFIL del backend (una prueba verifica que coincidan).
PROGRAMAS_POR_PERFIL = {
    'Realista': ['Licenciatura en Educación Física y Deporte', 'Ingeniería Ambiental', 'Diseño Industrial',
                 'Tecnología en Entrenamiento Deportivo', 'Ingeniería Industrial'],
    'Investigador': ['Ingeniería de Datos y Software', 'Ingeniería de Sistemas Cibernéticos', 'Ingeniería Ambiental',
                     'Ingeniería de Sonido', 'Psicología'],
    'Artístico': ['Arquitectura', 'Diseño de Modas', 'Ingeniería de Sonido', 'Diseño Industrial',
                  'Ingeniería Multimedia', 'Creación de Contenidos Digitales'],
    'Social': ['Psicología', 'Licenciatura en Educación Infantil', 'Derecho',
               'Licenciatura en Educación Física y Deporte'],
    'Emprendedor': ['Negocios Internacionales', 'Administración de Negocios', 'Derecho',
                    'Creación de Contenidos Digitales'],
    'Convencional': ['Contaduría Pública', 'Administración de Negocios', 'Ingeniería Industrial',
                     'Ingeniería de Datos y Software'],
}

# Margen (en puntos de porcentaje) para decir que dos campos del estudiante están "cerca".
MARGEN_DEFINICION = 10

# Recomendaciones del backend que solo repiten lo que la página ya muestra en
# otros capítulos (perfil, programas, ambiente). La del orientador pasa a "Qué sigue".
_PREFIJOS_REPETIDOS = (
    'Tu perfil vocacional Holland es',
    'Programas de pregrado de la USB',
    'Tu perfil secundario es',
    'Ambientes de trabajo ideales',
    'Se recomienda hablar con el orientador',
)


def campos_de(nombre_programa):
    """Campos RIASEC a los que pertenece un programa, en el orden R-I-A-S-E-C."""
    return [area for area in AREAS if nombre_programa in PROGRAMAS_POR_PERFIL.get(area, [])]


def _con_datos(p, grupo=None):
    return dict(p, url=URL_BASE + p['u'], campos=campos_de(p['n']), grupo=grupo)


def programas_recomendados(principal, secundario=None):
    """Programas del perfil principal y luego los del secundario que no se repiten.
    Cada uno lleva 'grupo' = 'principal' o 'secundario'."""
    por_nombre = {p['n']: p for p in PROGRAMAS}
    salida, vistos = [], set()
    for perfil, grupo in ((principal, 'principal'), (secundario, 'secundario')):
        for nombre in PROGRAMAS_POR_PERFIL.get(perfil or '', []):
            if nombre in por_nombre and nombre not in vistos:
                vistos.add(nombre)
                salida.append(_con_datos(por_nombre[nombre], grupo))
    return salida


def programas_para_mapa(principal, secundario=None):
    """Los 18 programas en su orden original, con 'campos' y 'grupo'
    ('principal', 'secundario' u 'otro') para el mapa vocacional."""
    grupo = {p['n']: p['grupo'] for p in programas_recomendados(principal, secundario)}
    return [_con_datos(p, grupo.get(p['n'], 'otro')) for p in PROGRAMAS]


def definicion_perfil(puntajes, margen=MARGEN_DEFINICION):
    """'marcado' si uno o dos campos se separan del resto; 'equilibrado' si tres
    o más quedan a menos de `margen` puntos del primero. None sin puntajes."""
    valores = sorted(
        ((float((d or {}).get('normalizado') or 0), area) for area, d in puntajes.items()),
        key=lambda x: -x[0],
    )
    if len(valores) < 3:
        return None
    tope = valores[0][0]
    cercanas = [area for v, area in valores if tope - v < margen]
    tipo = 'equilibrado' if len(cercanas) >= 3 else 'marcado'
    return {'tipo': tipo, 'areas': cercanas}


def sesiones_distintas(historial):
    """Número de días distintos con pruebas completadas. Las pruebas de Intereses
    y Competencias de un mismo día son una sola sesión, no dos momentos."""
    return len({h.get('fecha') for h in historial or [] if h.get('fecha')})


def recomendaciones_accionables(texto, descripcion=''):
    """Líneas de recomendación que no repiten lo que ya muestran otros capítulos."""
    lineas = [l.strip() for l in (texto or '').splitlines() if l.strip()]
    return [
        l for l in lineas
        if l != (descripcion or '').strip() and not l.startswith(_PREFIJOS_REPETIDOS)
    ]


_FORTALEZA = re.compile(r'^(?P<area>[^(:]+?)\s*\(\s*\d+(?:[.,]\d+)?\s*%\s*\)\s*:\s*(?P<texto>.*)$')


def fortalezas_sin_porcentaje(texto):
    """Fortalezas como (campo, descripción), sin el porcentaje que trae el backend:
    ese número es otro cálculo y no coincide con el de las barras de la página."""
    salida = []
    for linea in (texto or '').splitlines():
        linea = linea.strip().lstrip('•').strip()
        if not linea:
            continue
        m = _FORTALEZA.match(linea)
        salida.append((m.group('area').strip(), m.group('texto').strip()) if m else ('', linea))
    return salida


def areas_por_porcentaje(puntajes, ranking=None):
    """Campos de mayor a menor porcentaje combinado; los empates quedan en el
    orden del perfil (ranking) y, si no lo hay, en el orden R-I-A-S-E-C."""
    base = [a for a in (ranking or []) if a in puntajes]
    base += [a for a in AREAS if a in puntajes and a not in base]
    base += [a for a in puntajes if a not in base]
    return sorted(base, key=lambda a: -float((puntajes.get(a) or {}).get('normalizado') or 0))
