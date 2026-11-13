"""Tabla de análisis: una fila por estudiante con su último perfil completo.

Un perfil está completo cuando trae puntajes de las dos pruebas (Intereses y
Competencias). Si el estudiante solo hizo una, se usa la que tenga, marcada
como incompleta, para no perder la participación en los conteos.
"""

from ...extensions import db
from ...models.aplicacion import Aplicacion
from ...models.demografico import CampoDemografico, DatoDemografico
from ...models.escolar import PerfilEscolar, SedeEducativa
from ...models.resultado import PerfilVocacional
from .. import datos_escolares
from ..geo.geocodificador import distancia_m

AREAS = ['Realista', 'Investigador', 'Artístico', 'Social', 'Emprendedor', 'Convencional']


def porcentajes_por_area(datos_json):
    por_area = (datos_json or {}).get('puntajes_por_area') or {}
    interes, competencia, combinado = {}, {}, {}
    for area in AREAS:
        a = por_area.get(area) or {}
        if a.get('interes_maximo'):
            interes[area] = float(a.get('interes_normalizado') or 0)
        if a.get('competencia_maximo'):
            competencia[area] = float(a.get('competencia_porcentaje') or 0)
        combinado[area] = float(a.get('normalizado') or 0)
    return interes, competencia, combinado


def filas(incluir_simulados=False):
    escolares = datos_escolares.por_usuario(incluir_simulados=True)
    genero_campo = CampoDemografico.query.filter_by(nombre='genero').first()
    generos = {}
    if genero_campo:
        generos = dict(db.session.query(DatoDemografico.usuario_id, DatoDemografico.valor)
                       .filter(DatoDemografico.campo_id == genero_campo.id).all())
    perfiles_escolares = {p.usuario_id: p for p in PerfilEscolar.query.all()}
    sedes = {s.codigo: s for s in SedeEducativa.query.all()}

    registros = (db.session.query(Aplicacion.usuario_id, Aplicacion.fecha_fin, PerfilVocacional)
                 .join(PerfilVocacional, PerfilVocacional.aplicacion_id == Aplicacion.id)
                 .filter(Aplicacion.estado == 'completada')
                 .order_by(Aplicacion.usuario_id, Aplicacion.fecha_fin).all())

    por_usuario = {}
    for usuario_id, fecha, perfil in registros:
        interes, competencia, combinado = porcentajes_por_area(perfil.datos_json)
        completo = len(interes) == 6 and len(competencia) == 6
        u = por_usuario.setdefault(usuario_id, {'perfiles': [], 'ultimo': None, 'ultimo_completo': None})
        dato = {'fecha': fecha, 'principal': perfil.perfil_principal, 'secundario': perfil.perfil_secundario,
                'interes': interes, 'competencia': competencia, 'combinado': combinado, 'completo': completo}
        u['ultimo'] = dato
        if completo:
            u['ultimo_completo'] = dato
            u['perfiles'].append(dato)

    salida = []
    for usuario_id, u in por_usuario.items():
        esc = escolares.get(usuario_id) or {}
        if esc.get('simulado') and not incluir_simulados:
            continue
        p = u['ultimo_completo'] or u['ultimo']
        ordenados = sorted(p['combinado'].values(), reverse=True)
        pe = perfiles_escolares.get(usuario_id)
        sede = sedes.get(pe.sede_codigo) if pe and pe.sede_codigo else None
        distancia = None
        if pe and pe.lat is not None and sede and sede.lat is not None:
            distancia = distancia_m(pe.lat, pe.lon, sede.lat, sede.lon)
        # Sesiones en fechas distintas, para ver si el perfil se mantiene al repetir.
        sesiones, vistos = [], set()
        for d in u['perfiles']:
            dia = d['fecha'].date() if d['fecha'] else None
            if dia not in vistos:
                vistos.add(dia)
                sesiones.append(d['principal'])
        salida.append({
            'usuario_id': usuario_id,
            'principal': p['principal'], 'secundario': p['secundario'], 'completo': p['completo'],
            'interes': p['interes'], 'competencia': p['competencia'], 'combinado': p['combinado'],
            'distancia_1_2': (ordenados[0] - ordenados[1]) if len(ordenados) > 1 else None,
            'genero': generos.get(usuario_id),
            'grado': esc.get('grado'), 'sector': esc.get('sector'), 'edad': esc.get('edad'),
            'municipio': esc.get('municipio'), 'estrato': esc.get('estrato'),
            'colegio_codigo': pe.sede_codigo if pe else None, 'colegio': esc.get('colegio'),
            'lat': pe.lat if pe else None, 'lon': pe.lon if pe else None,
            'distancia_colegio_m': distancia,
            'sesiones': sesiones,
            'simulado': bool(esc.get('simulado')),
        })
    return salida


def firma():
    """Huella barata de los datos: si no cambia, la caché sigue sirviendo."""
    apps = db.session.query(db.func.count(Aplicacion.id), db.func.max(Aplicacion.fecha_fin)) \
        .filter(Aplicacion.estado == 'completada').one()
    esc = db.session.query(db.func.count(PerfilEscolar.id), db.func.max(PerfilEscolar.updated_at)).one()
    return (apps[0], str(apps[1]), esc[0], str(esc[1]))
