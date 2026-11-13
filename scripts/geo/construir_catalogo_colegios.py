"""Construye el catálogo de colegios (oficiales y privados) del Valle de Aburrá.

Solo entran las sedes que dan algún grado entre 9° y 11°, que son las que
aplican la prueba. Fuentes, de la más precisa a la menos:

1. Medellín: capa "Sedes Educativas" de la Alcaldía (servidor de mapas, vigencia
   2024), con coordenadas, comuna, barrio y matrícula por grado.
2. Envigado: "Instituciones Educativas Municipio de Envigado" (datos.gov.co,
   g8hy-gwg8), con coordenadas.
3. Los otros ocho municipios: directorio de establecimientos del Ministerio de
   Educación (datos.gov.co, upkm-vdjb). Trae dirección pero no coordenadas: se
   ubican con el índice local de direcciones y, si no aparecen, con el colegio
   del mismo nombre en OpenStreetMap.

El primer dígito del código DANE dice el sector: 1 y 2 oficial, 3 y 4 privado.

Salida: backend/app/recursos/geo/colegios_valle_aburra.json

Uso:
    python scripts/geo/construir_catalogo_colegios.py
"""

import difflib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / 'backend'))

from app.services.geo.direcciones import municipio_canonico, sin_tildes  # noqa: E402
from app.services.geo import geocodificador  # noqa: E402

SALIDA = RAIZ / 'backend' / 'app' / 'recursos' / 'geo' / 'colegios_valle_aburra.json'
AGENTE = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36'}
CAPA_MEDELLIN = 'https://www.medellin.gov.co/servidormapas/rest/services/educacion/VC_Sedes_Instituciones/MapServer/0/query'
ENVIGADO = 'https://www.datos.gov.co/resource/g8hy-gwg8.json'
MINISTERIO = 'https://www.datos.gov.co/resource/upkm-vdjb.json'
# Servidores públicos de Overpass; si uno falla se prueba el siguiente.
OVERPASS = ('https://overpass-api.de/api/interpreter',
            'https://overpass.kumi.systems/api/interpreter',
            'https://maps.mail.ru/osm/tools/overpass/api/interpreter')
OTROS = ('BELLO', 'ITAGUI', 'SABANETA', 'LA ESTRELLA', 'CALDAS', 'COPACABANA', 'GIRARDOTA', 'BARBOSA')


def leer_json(url, datos=None):
    pedido = urllib.request.Request(url, data=datos, headers=AGENTE)
    with urllib.request.urlopen(pedido, timeout=120) as r:
        return json.loads(r.read().decode('utf-8'))


# Palabras que las fuentes escriben sin tilde.
TILDES = {'Institucion': 'Institución', 'Educacion': 'Educación', 'Tecnica': 'Técnica', 'Tecnico': 'Técnico',
          'Tecnologico': 'Tecnológico', 'Academico': 'Académico', 'Academia': 'Academia', 'Basica': 'Básica',
          'Jesus': 'Jesús', 'Maria': 'María', 'Jose': 'José', 'Angel': 'Ángel', 'Bolivar': 'Bolívar',
          'Garcia': 'García', 'Gomez': 'Gómez', 'Martinez': 'Martínez', 'Rodriguez': 'Rodríguez',
          'Gonzalez': 'González', 'Lopez': 'López', 'Perez': 'Pérez', 'Ramirez': 'Ramírez', 'Sanchez': 'Sánchez',
          'Dario': 'Darío', 'Simon': 'Simón', 'Ines': 'Inés', 'Ramon': 'Ramón', 'Concepcion': 'Concepción',
          'Asuncion': 'Asunción', 'Anunciacion': 'Anunciación', 'Ingles': 'Inglés', 'Frances': 'Francés',
          'Aleman': 'Alemán', 'Cristobal': 'Cristóbal', 'Medellin': 'Medellín', 'Itagui': 'Itagüí',
          'Comunitario': 'Comunitario', 'Pedagogico': 'Pedagógico', 'Catolico': 'Católico', 'Biblico': 'Bíblico'}


def titulo(texto):
    """Mayúscula inicial respetando siglas cortas (I.E., IE, CER...)."""
    texto = re.sub(r'\s+', ' ', (texto or '').strip())
    palabras = []
    for p in texto.split(' '):
        if len(p) <= 3 and p.isupper() and p not in ('DE', 'LA', 'EL', 'LOS', 'LAS', 'DEL', 'Y'):
            palabras.append(p)
        else:
            palabras.append(p.capitalize() if p.isupper() or p.islower() else p)
    return ' '.join(w.lower() if w.lower() in ('de', 'la', 'el', 'los', 'las', 'del', 'y') and i else TILDES.get(w, w)
                    for i, w in enumerate(palabras))


def sector_por_codigo(codigo):
    return 'Oficial' if str(codigo)[:1] in ('1', '2') else 'Privado'


def medellin():
    filas, desplazamiento = [], 0
    while True:
        q = urllib.parse.urlencode({'where': '1=1', 'outFields': '*', 'returnGeometry': 'false', 'f': 'json',
                                    'resultOffset': desplazamiento, 'resultRecordCount': 1000})
        lote = leer_json(f'{CAPA_MEDELLIN}?{q}')['features']
        filas += [f['attributes'] for f in lote]
        if len(lote) < 1000:
            break
        desplazamiento += 1000
    salida = []
    for a in filas:
        m9, m10, m11 = (int(a.get(f'grado{g}') or 0) for g in (9, 10, 11))
        if (m9 + m10 + m11) == 0 or (a.get('estado') or '').lower() != 'activo' or not a.get('latitud'):
            continue
        salida.append({
            'codigo': str(a['cons_sede']), 'codigo_establecimiento': str(a.get('codigo_dan') or ''),
            'nombre': titulo(a['nombre_est']), 'sede': titulo(a.get('sede_educa')),
            'sector': 'Oficial' if a.get('sector') == 'Oficial' else 'Privado',
            'municipio': 'MEDELLIN', 'comuna': titulo(a.get('nombre_com')), 'barrio': titulo(a.get('nombre_bar')),
            'direccion': (a.get('direccion') or '').strip(), 'lat': round(a['latitud'], 6), 'lon': round(a['longitud'], 6),
            'matricula_9': m9, 'matricula_10': m10, 'matricula_11': m11,
            'fuente': 'Alcaldía de Medellín, Sedes Educativas (2024)', 'ubicacion': 'oficial',
        })
    return salida


def envigado():
    salida = []
    for e in leer_json(f'{ENVIGADO}?$limit=500'):
        if e.get('nivel_de_escolaridad_media') != 'Si' or not e.get('coordenadas'):
            continue
        salida.append({
            'codigo': str(e['c_digo_dane']), 'codigo_establecimiento': str(e['c_digo_dane']),
            'nombre': titulo(e['nombre_ie']), 'sede': titulo(e['nombre_ie']),
            'sector': 'Oficial' if e.get('tipo_ie') == 'Oficial' else 'Privado',
            'municipio': 'ENVIGADO', 'comuna': None, 'barrio': None,
            'direccion': (e.get('direcci_n') or '').strip(),
            'lat': round(float(e['coordenadas']['latitude']), 6), 'lon': round(float(e['coordenadas']['longitude']), 6),
            'matricula_9': None, 'matricula_10': None, 'matricula_11': None,
            'fuente': 'Alcaldía de Envigado, Instituciones Educativas (2024)', 'ubicacion': 'oficial',
        })
    return salida


def colegios_osm():
    consulta = '[out:json][timeout:90];nwr["amenity"="school"](6.00,-75.72,6.50,-75.30);out center tags;'
    datos, errores = None, []
    for servidor in OVERPASS:
        try:
            datos = leer_json(servidor, urllib.parse.urlencode({'data': consulta}).encode())
            break
        except Exception as exc:
            errores.append(f'{servidor}: {exc}')
    if datos is None:
        print('Aviso: OpenStreetMap no respondió; se sigue sin ubicación de respaldo.')
        for e in errores:
            print('  ', e)
        return []
    salida = []
    for e in datos['elements']:
        nombre = e.get('tags', {}).get('name')
        c = e.get('center', e)
        if nombre and 'lat' in c:
            salida.append((sin_tildes(nombre).upper(), c['lat'], c['lon']))
    return salida


def parecido(a, b):
    ruido = r'\b(INSTITUCION|EDUCATIVA|COLEGIO|I\.? ?E\.?|CENTRO|ESCUELA|LICEO|SEDE|DE|LA|EL|DEL|LOS|LAS)\b'
    a = re.sub(ruido, ' ', sin_tildes(a).upper())
    b = re.sub(ruido, ' ', b)
    return difflib.SequenceMatcher(None, ' '.join(a.split()), ' '.join(b.split())).ratio()


def ministerio(osm):
    filtro = ("codigodepartamento='05' AND nombremunicipio in("
              + ','.join(f"'{m}'" for m in OTROS) + ')')
    q = urllib.parse.urlencode({'$where': filtro, '$limit': 5000})
    salida, sin_ubicar = [], []
    for e in leer_json(f'{MINISTERIO}?{q}'):
        grados = {g.strip() for g in (e.get('grados') or '').split(',')}
        if not grados & {'9', '10', '11'}:
            continue
        mpio = municipio_canonico(e['nombremunicipio'])
        nombre = titulo(e['nombreestablecimiento'])
        direccion = (e.get('direccion') or '').strip()
        r = geocodificador.geocodificar(direccion, mpio, usar_osm=False)
        if r['encontrada']:
            lat, lon, como = r['lat'], r['lon'], f"direccion_{r['precision']}"
        else:
            centro = geocodificador.CENTROS_MUNICIPIO[mpio]
            cercanos = [o for o in osm if geocodificador.distancia_m(centro[0], centro[1], o[1], o[2]) < 9000]
            mejor = max(cercanos, key=lambda o: parecido(nombre, o[0]), default=None)
            if mejor and parecido(nombre, mejor[0]) >= 0.72:
                lat, lon, como = mejor[1], mejor[2], 'openstreetmap'
            else:
                sin_ubicar.append(f'{mpio}: {nombre} ({direccion})')
                continue
        salida.append({
            'codigo': str(e['codigoestablecimiento']), 'codigo_establecimiento': str(e['codigoestablecimiento']),
            'nombre': nombre, 'sede': nombre, 'sector': sector_por_codigo(e['codigoestablecimiento']),
            'municipio': mpio, 'comuna': None, 'barrio': None, 'direccion': direccion,
            'lat': round(lat, 6), 'lon': round(lon, 6),
            'matricula_9': None, 'matricula_10': None, 'matricula_11': None,
            'fuente': 'Ministerio de Educación, directorio de establecimientos (2016)', 'ubicacion': como,
        })
    return salida, sin_ubicar


def main():
    t0 = time.time()
    if not geocodificador.hay_indice():
        print('Aviso: no está el índice de direcciones; los colegios fuera de Medellín y Envigado '
              'se ubicarán solo por OpenStreetMap.')
    med = medellin()
    env = envigado()
    osm = colegios_osm()
    otros, sin_ubicar = ministerio(osm)
    vistos, catalogo = set(), []
    for c in med + env + otros:
        if c['codigo'] in vistos:
            continue
        vistos.add(c['codigo'])
        catalogo.append(c)
    catalogo.sort(key=lambda c: (c['municipio'], c['nombre'], c['sede']))
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    documento = {
        'generado': time.strftime('%Y-%m-%d'),
        'fuentes': sorted({c['fuente'] for c in catalogo}) + ['OpenStreetMap (ubicación de respaldo), ODbL'],
        'colegios': catalogo,
    }
    SALIDA.write_text(json.dumps(documento, ensure_ascii=False, indent=1), encoding='utf-8')
    por = {}
    for c in catalogo:
        por.setdefault((c['municipio'], c['sector']), 0)
        por[(c['municipio'], c['sector'])] += 1
    print(f'{len(catalogo)} colegios en {time.time() - t0:.0f} s -> {SALIDA}')
    for (m, s), n in sorted(por.items()):
        print(f'  {m:12} {s:8} {n}')
    print(f'Sin ubicar ({len(sin_ubicar)}):')
    for s in sin_ubicar:
        print('  ', s)


if __name__ == '__main__':
    main()
