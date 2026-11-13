"""Estadística avanzada: hallazgos recalculados a medida que llegan encuestas."""

import threading
import time

from . import datos, hallazgos

_cache = {}
_lock = threading.Lock()
VIGENCIA_S = 60


def estadistica_avanzada(incluir_simulados=False):
    """Las tarjetas de hallazgos. Se recalculan si cambian los datos o pasan 60 s."""
    firma = datos.firma()
    clave = bool(incluir_simulados)
    with _lock:
        guardado = _cache.get(clave)
        if guardado and guardado['firma'] == firma and time.time() - guardado['hora'] < VIGENCIA_S:
            return guardado['respuesta']
    filas = datos.filas(incluir_simulados=incluir_simulados)
    respuesta = {
        'tarjetas': hallazgos.todos(filas),
        'estudiantes': len(filas),
        'con_dos_pruebas': sum(1 for f in filas if f['completo']),
        'simulados_incluidos': clave,
        'simulados_en_base': None,
        'calculado': time.strftime('%Y-%m-%dT%H:%M:%S'),
    }
    with _lock:
        _cache[clave] = {'firma': firma, 'hora': time.time(), 'respuesta': respuesta}
    return respuesta


def mapa(incluir_simulados=False):
    """Puntos de estudiantes (sin nombres) y colegios con su cobertura, para el mapa de Bienestar."""
    from collections import Counter
    from ...models.escolar import SedeEducativa
    filas = datos.filas(incluir_simulados=incluir_simulados)
    estudiantes = [{
        'lat': f['lat'], 'lon': f['lon'], 'perfil': f['principal'], 'grado': f['grado'], 'sector': f['sector'],
        'estrato': f['estrato'], 'municipio': f['municipio'], 'colegio': f['colegio'], 'genero': f['genero'],
        'colegio_codigo': f['colegio_codigo'],
        'simulado': f['simulado'],
        'distancia_km': round(f['distancia_colegio_m'] / 1000, 2) if f['distancia_colegio_m'] is not None else None,
    } for f in filas if f['lat'] is not None]
    por_colegio = {}
    for f in filas:
        if f['colegio_codigo']:
            por_colegio.setdefault(f['colegio_codigo'], Counter())[f['principal']] += 1
    colegios = []
    for s in SedeEducativa.query.filter(SedeEducativa.lat.isnot(None)).all():
        conteo = por_colegio.get(s.codigo, Counter())
        evaluados = sum(conteo.values())
        matricula = s.matricula_media
        colegios.append({
            'codigo': s.codigo, 'nombre': s.nombre_visible, 'sector': s.sector, 'municipio': s.municipio,
            'comuna': s.comuna, 'lat': s.lat, 'lon': s.lon, 'matricula': matricula, 'evaluados': evaluados,
            'cobertura': (evaluados / matricula) if matricula else None,
            'dominante': conteo.most_common(1)[0][0] if conteo else None,
            'perfiles': dict(conteo),
        })
    return {'estudiantes': estudiantes, 'colegios': colegios, 'simulados_incluidos': bool(incluir_simulados)}
