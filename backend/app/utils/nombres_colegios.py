"""Presentación de los nombres del catálogo de colegios.

El catálogo viene de las alcaldías y del Ministerio de Educación, y trae los nombres
como los escribieron allá: abreviados ("IE", "COL", "C.e."), con palabras en mayúscula
sostenida ("SAN José") y casi siempre sin tildes. Aquí se arreglan solo para mostrarlos;
el dato original no se toca.
"""

import re
import unicodedata
from functools import lru_cache

# Abreviaturas con las que empieza el nombre en el catálogo.
_PREFIJO = re.compile(r'^([IC])\s*\.?\s*E\s*\.?\s*(R)?\s*\.?\s+', re.IGNORECASE)
_PREFIJO_PALABRA = {'COL': 'Colegio', 'INT': 'Instituto', 'IER': 'Institución Educativa Rural',
                    'IE': 'Institución Educativa', 'CER': 'Centro Educativo Rural', 'CE': 'Centro Educativo'}

# Siglas que se quedan en mayúscula sostenida.
SIGLAS = {'ABC', 'TIC', 'SENA', 'UCN', 'USB', 'INEM', 'ONU', 'IDEM'}
# Números romanos que vienen mal escritos ("Leon Xiii").
ROMANOS = {'II', 'III', 'IV', 'VI', 'VII', 'VIII', 'IX', 'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XXIII'}
# Palabras que van en minúscula dentro del nombre.
ENLACES = {'de', 'del', 'la', 'las', 'los', 'el', 'y', 'e', 'en', 'al', 'a', 'con', 'para', 'por'}
# Artículos que sí se escriben con mayúscula cuando abren el nombre propio.
ARTICULOS = {'el', 'la', 'los', 'las'}
# Tipos de institución: lo que va después de ellos es el nombre propio.
TIPOS = ('institucion educativa rural', 'institucion educativa', 'centro educativo rural',
         'centro educativo', 'unidad educativa', 'colegio', 'instituto', 'liceo', 'gimnasio', 'escuela')

# El catálogo viene sin tildes. Estas son las palabras que aparecen en él y sí la llevan.
TILDES = {
    'seccion': 'Sección', 'alegria': 'Alegría', 'velez': 'Vélez', 'mejia': 'Mejía',
    'echavarria': 'Echavarría', 'presentacion': 'Presentación', 'corazon': 'Corazón',
    'galan': 'Galán', 'asis': 'Asís', 'marquez': 'Márquez', 'gaitan': 'Gaitán',
    'andres': 'Andrés', 'hernan': 'Hernán', 'jovenes': 'Jóvenes', 'vasquez': 'Vásquez',
    'hernandez': 'Hernández', 'angeles': 'Ángeles', 'calderon': 'Calderón',
    'alcazares': 'Alcázares', 'cespedes': 'Céspedes', 'lideres': 'Líderes', 'guzman': 'Guzmán',
    'leon': 'León', 'niquia': 'Niquía', 'paris': 'París', 'roldan': 'Roldán',
    'eucaristia': 'Eucaristía', 'union': 'Unión', 'alvarez': 'Álvarez', 'gutierrez': 'Gutiérrez',
    'martin': 'Martín', 'cortes': 'Cortés', 'multiples': 'Múltiples', 'lujan': 'Luján',
    'congregacion': 'Congregación', 'corporacion': 'Corporación', 'alcaldia': 'Alcaldía',
    'suarez': 'Suárez', 'maria': 'María', 'jose': 'José', 'nicolas': 'Nicolás',
    'ramon': 'Ramón', 'simon': 'Simón', 'ines': 'Inés', 'angel': 'Ángel', 'bolivar': 'Bolívar',
    'concepcion': 'Concepción', 'educacion': 'Educación', 'republica': 'República',
    'sofia': 'Sofía', 'chiquinquira': 'Chiquinquirá', 'panama': 'Panamá', 'jimenez': 'Jiménez',
    'belen': 'Belén', 'medellin': 'Medellín', 'jesus': 'Jesús', 'fatima': 'Fátima',
    'sebastian': 'Sebastián', 'cristobal': 'Cristóbal', 'joaquin': 'Joaquín',
    'agustin': 'Agustín', 'martinez': 'Martínez', 'ramirez': 'Ramírez', 'rodriguez': 'Rodríguez',
    'gomez': 'Gómez', 'perez': 'Pérez', 'diaz': 'Díaz', 'garces': 'Garcés', 'valdes': 'Valdés',
    'tomas': 'Tomás', 'lucia': 'Lucía', 'rocio': 'Rocío', 'pedagogico': 'Pedagógico',
    'tecnico': 'Técnico', 'tecnica': 'Técnica', 'politecnico': 'Politécnico',
    'politecnica': 'Politécnica', 'informatica': 'Informática', 'musica': 'Música',
    'america': 'América', 'cordoba': 'Córdoba', 'caceres': 'Cáceres', 'maximo': 'Máximo',
    'cesar': 'César', 'hector': 'Héctor', 'oscar': 'Óscar', 'victor': 'Víctor',
    'felix': 'Félix', 'ruben': 'Rubén', 'dario': 'Darío', 'eliecer': 'Eliécer',
    'efrain': 'Efraín', 'fabian': 'Fabián', 'damaso': 'Dámaso', 'julian': 'Julián',
    'bethlemitas': 'Bethlemitas', 'teologia': 'Teología', 'filosofia': 'Filosofía',
    'presbitero': 'Presbítero', 'munera': 'Múnera', 'elias': 'Elías', 'macias': 'Macías',
    'compania': 'Compañía', 'castrillon': 'Castrillón', 'innovacion': 'Innovación',
    'colon': 'Colón', 'arbelaez': 'Arbeláez', 'beltran': 'Beltrán', 'belalcazar': 'Belalcázar',
    'playon': 'Playón', 'arquidiocesis': 'Arquidiócesis', 'benjamin': 'Benjamín',
    'santamaria': 'Santamaría', 'agrupacion': 'Agrupación', 'rosalia': 'Rosalía',
    'autonomo': 'Autónomo', 'autonoma': 'Autónoma',
}


def sin_tildes(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto or '') if unicodedata.category(c) != 'Mn')


def _palabra(w, primera):
    """Arregla una palabra suelta: mayúscula sostenida, número romano, tilde y enlaces."""
    letras = re.sub(r'[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ]', '', w)
    if letras.upper() in SIGLAS:
        return w.upper()
    if letras.upper() in ROMANOS and len(letras) == len(w):
        return w.upper()
    clave = sin_tildes(letras).lower()
    if clave in TILDES:
        return w.replace(letras, TILDES[clave])
    if not primera and clave in ENLACES:
        return w.lower()
    if letras.isupper() and len(letras) >= 2:
        return w.capitalize()
    if letras.islower():
        return w.capitalize()
    return w


@lru_cache(maxsize=4096)
def limpiar_nombre(texto):
    """"COL ANA María Janer" -> "Colegio Ana María Janer".

    Se guarda en caché porque el buscador recorre el catálogo entero en cada búsqueda.
    """
    nombre = re.sub(r'\s+', ' ', (texto or '').strip())
    if not nombre:
        return ''
    # "Lusitania- Paz de Colombia" -> "Lusitania - Paz de Colombia".
    nombre = re.sub(r'(?<=\S)-\s+|\s+-(?=\S)', ' - ', nombre)
    m = _PREFIJO.match(nombre)
    if m:
        sigla = (m.group(1) + 'E' + (m.group(2) or '')).upper()
        nombre = f'{_PREFIJO_PALABRA[sigla]} {nombre[m.end():]}'
    else:
        primera = nombre.split(' ')[0].upper().strip('.')
        if primera in ('COL', 'INT'):
            nombre = f'{_PREFIJO_PALABRA[primera]} {nombre.split(" ", 1)[1]}' if ' ' in nombre else nombre

    palabras = [_palabra(w, i == 0) for i, w in enumerate(nombre.split(' '))]
    # Si el nombre propio empieza por artículo, va con mayúscula: "Colegio la Salle" -> "La Salle".
    plano = sin_tildes(' '.join(palabras)).lower()
    for tipo in TIPOS:
        if plano.startswith(tipo + ' '):
            i = len(tipo.split(' '))
            if i < len(palabras) and palabras[i].lower() in ARTICULOS:
                palabras[i] = palabras[i].capitalize()
            break
    return ' '.join(palabras)


@lru_cache(maxsize=4096)
def etiqueta_sede(nombre, sede):
    """Devuelve "Sede X" cuando la sede es distinta del colegio, o None si es la principal."""
    if not sede or not nombre or sin_tildes(sede).lower().strip() == sin_tildes(nombre).lower().strip():
        return None
    texto = re.sub(r'^\s*(secci[oó]n|sede)\s+', '', sede.strip(), flags=re.IGNORECASE)
    texto = re.sub(r'^\s*escuela\s+', '', texto, flags=re.IGNORECASE)
    return f'Sede {limpiar_nombre(texto)}' if texto.strip() else f'Sede {limpiar_nombre(sede)}'


def nombre_con_sede(nombre, sede):
    """"Institución Educativa Alfonso López — Sede Municipal Kennedy"."""
    limpio = limpiar_nombre(nombre)
    etiqueta = etiqueta_sede(nombre, sede)
    return f'{limpio} — {etiqueta}' if etiqueta else limpio


def nombre_municipio(municipio):
    """"MEDELLIN" -> "Medellín"."""
    if not municipio:
        return ''
    return municipio.title().replace('Itagui', 'Itagüí').replace('Medellin', 'Medellín')
