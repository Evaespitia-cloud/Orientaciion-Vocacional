"""Geocodificador de direcciones del Valle de Aburrá.

Orden de búsqueda, de más a menos preciso:

1. ``exacta``: la dirección está en el índice local (catastro de medidores de EPM).
2. ``interpolada``: la placa no está, pero sí otras de la misma cuadra; se
   interpola entre la placa anterior y la siguiente.
3. ``cuadra``: solo hay placas a un lado; se usa la más cercana.
4. ``osm``: Nominatim (OpenStreetMap), limitado a una consulta por segundo.
5. Nada: el estudiante pone el pin a mano (``manual``).

Si la dirección trae SUR al final ("# 43-21 sur") no se sabe si es de la vía
principal o del cruce: se prueban las dos lecturas.
"""

import json
import math
import os
import sqlite3
import threading
import time
import urllib.parse
import urllib.request
from dataclasses import replace

from .direcciones import normalizar, municipio_canonico

# Caja del Valle de Aburrá (oeste, norte, este, sur) para acotar Nominatim.
CAJA_VALLE = (-75.72, 6.50, -75.30, 6.00)
CENTROS_MUNICIPIO = {
    'MEDELLIN': (6.2442, -75.5812), 'BELLO': (6.3373, -75.5580), 'ITAGUI': (6.1719, -75.6114),
    'ENVIGADO': (6.1759, -75.5917), 'SABANETA': (6.1515, -75.6166), 'CALDAS': (6.0911, -75.6357),
    'COPACABANA': (6.3463, -75.5089), 'LA ESTRELLA': (6.1576, -75.6431), 'BARBOSA': (6.4389, -75.3317),
    'GIRARDOTA': (6.3775, -75.4448),
}
# Placas más lejanas que esto no sirven para aproximar (en número de placa).
MAX_SALTO_PLACA = 40

_CAMPOS = ('via', 'n1', 'l1', 'bis1', 's1', 'n2', 'l2', 'bis2', 's2')
_lock_osm = threading.Lock()
_ultima_osm = [0.0]


def ruta_indice():
    por_defecto = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'instance', 'direcciones_valle.sqlite')
    return os.path.abspath(os.getenv('INDICE_DIRECCIONES', por_defecto))


def hay_indice(ruta=None):
    return os.path.exists(ruta or ruta_indice())


def _conectar(ruta):
    con = sqlite3.connect(f'file:{ruta}?mode=ro', uri=True, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def _lecturas(d):
    """La dirección tal cual y, si el SUR pudo ser de la vía principal, la otra lectura."""
    yield d
    if d.s2 and not d.s1:
        yield replace(d, s1=True, s2=False)
    if d.via in ('CL', 'CR'):
        yield replace(d, via='AVDA')
    elif d.via == 'AVDA':
        yield replace(d, via='CR')
        yield replace(d, via='CL')


def _buscar_en_indice(con, d, municipio):
    valores = [municipio] + [int(v) if isinstance(v, bool) else v for v in (getattr(d, c) for c in _CAMPOS)]
    filas = con.execute(
        f'SELECT placa, lat, lon, estrato FROM direcciones WHERE municipio = ? AND '
        + ' AND '.join(f'{c} = ?' for c in _CAMPOS) + ' ORDER BY placa', valores).fetchall()
    if not filas:
        return None
    for f in filas:
        if f['placa'] == d.placa:
            return {'lat': f['lat'], 'lon': f['lon'], 'estrato': f['estrato'], 'precision': 'exacta'}
    antes = [f for f in filas if f['placa'] < d.placa]
    despues = [f for f in filas if f['placa'] > d.placa]
    if antes and despues:
        a, b = antes[-1], despues[0]
        if b['placa'] - a['placa'] <= 2 * MAX_SALTO_PLACA:
            t = (d.placa - a['placa']) / (b['placa'] - a['placa'])
            return {'lat': a['lat'] + t * (b['lat'] - a['lat']), 'lon': a['lon'] + t * (b['lon'] - a['lon']),
                    'estrato': a['estrato'] if t < 0.5 else b['estrato'], 'precision': 'interpolada'}
    cercana = min(filas, key=lambda f: abs(f['placa'] - d.placa))
    if abs(cercana['placa'] - d.placa) <= MAX_SALTO_PLACA:
        return {'lat': cercana['lat'], 'lon': cercana['lon'], 'estrato': cercana['estrato'], 'precision': 'cuadra'}
    return None


def _nominatim(texto, municipio):
    """Consulta a Nominatim respetando su política: una por segundo y con agente propio."""
    consulta = {
        'q': f'{texto}, {municipio.title()}, Antioquia, Colombia', 'format': 'jsonv2', 'limit': 1,
        'countrycodes': 'co', 'viewbox': ','.join(str(v) for v in CAJA_VALLE), 'bounded': 1,
    }
    url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode(consulta)
    pedido = urllib.request.Request(url, headers={
        'User-Agent': 'OrientacionVocacional-USB/1.0 (proyecto academico, Universidad de San Buenaventura Medellin)'})
    with _lock_osm:
        espera = 1.0 - (time.time() - _ultima_osm[0])
        if espera > 0:
            time.sleep(espera)
        _ultima_osm[0] = time.time()
        try:
            with urllib.request.urlopen(pedido, timeout=6) as r:
                datos = json.loads(r.read().decode('utf-8'))
        except Exception:
            return None
    if not datos:
        return None
    return {'lat': float(datos[0]['lat']), 'lon': float(datos[0]['lon']), 'estrato': None, 'precision': 'osm'}


def geocodificar(texto, municipio, ruta=None, usar_osm=None):
    """Ubica una dirección escrita. Devuelve siempre un dict con ``encontrada``.

    ``usar_osm`` por defecto sigue la variable GEOCODIFICAR_OSM (1 si no está).
    """
    if usar_osm is None:
        usar_osm = os.getenv('GEOCODIFICAR_OSM', '1') != '0'
    mpio = municipio_canonico(municipio)
    d = normalizar(texto)
    respuesta = {
        'encontrada': False, 'municipio': mpio,
        'normalizada': d.texto() if d else None, 'complemento': d.complemento if d else '',
        'centro': CENTROS_MUNICIPIO.get(mpio),
    }
    if not mpio:
        respuesta['motivo'] = 'municipio'
        return respuesta
    if d is None:
        respuesta['motivo'] = 'formato'
        return respuesta

    ruta = ruta or ruta_indice()
    if hay_indice(ruta):
        con = _conectar(ruta)
        try:
            for lectura in _lecturas(d):
                hallada = _buscar_en_indice(con, lectura, mpio)
                if hallada:
                    respuesta.update(hallada, encontrada=True, normalizada=lectura.texto())
                    return respuesta
        finally:
            con.close()

    if usar_osm:
        sin_complemento = texto.split(d.complemento)[0] if d.complemento else texto
        hallada = _nominatim(sin_complemento.strip(), mpio)
        if hallada:
            respuesta.update(hallada, encontrada=True)
            return respuesta
    respuesta['motivo'] = 'sin_resultado'
    return respuesta


def distancia_m(lat1, lon1, lat2, lon2):
    """Distancia en metros entre dos puntos (haversine)."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def estrato_cercano(lat, lon, ruta=None, radio_m=40):
    """Estrato de la dirección del índice más cercana a un pin, si está a menos de ``radio_m``."""
    ruta = ruta or ruta_indice()
    if not hay_indice(ruta):
        return None
    ci, cj = round(lat * 1000), round(lon * 1000)
    celdas = [f'{ci + a}:{cj + b}' for a in (-1, 0, 1) for b in (-1, 0, 1)]
    con = _conectar(ruta)
    try:
        filas = con.execute(
            f'SELECT lat, lon, estrato FROM direcciones WHERE celda IN ({",".join("?" * len(celdas))}) '
            'AND estrato IS NOT NULL', celdas).fetchall()
    finally:
        con.close()
    mejor = min(filas, key=lambda f: distancia_m(lat, lon, f['lat'], f['lon']), default=None)
    if mejor and distancia_m(lat, lon, mejor['lat'], mejor['lon']) <= radio_m:
        return mejor['estrato']
    return None
