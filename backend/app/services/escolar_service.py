"""Catálogo de colegios y perfil escolar (colegio, edad y dirección) del estudiante."""

import json
import os
import re

from ..extensions import db
from ..models.escolar import SedeEducativa, PerfilEscolar
from .geo import geocodificador
from .geo.direcciones import municipio_canonico, sin_tildes

RUTA_CATALOGO = os.path.join(os.path.dirname(__file__), '..', 'recursos', 'geo', 'colegios_valle_aburra.json')
EDAD_MIN, EDAD_MAX = 12, 25
# En el catálogo el sector es "Oficial" o "Privado"; el estudiante responde "público" o "privado".
SECTORES = {'OFICIAL': 'Oficial', 'PUBLICO': 'Oficial', 'PRIVADO': 'Privado'}


def cargar_catalogo(ruta=RUTA_CATALOGO):
    """Inserta o actualiza las sedes del archivo. Devuelve cuántas quedaron."""
    with open(ruta, encoding='utf-8') as f:
        colegios = json.load(f)['colegios']
    existentes = {s.codigo: s for s in SedeEducativa.query.all()}
    campos = ('codigo_establecimiento', 'nombre', 'sede', 'sector', 'municipio', 'comuna', 'barrio', 'direccion',
              'lat', 'lon', 'matricula_9', 'matricula_10', 'matricula_11', 'fuente', 'ubicacion')
    for c in colegios:
        sede = existentes.get(c['codigo']) or SedeEducativa(codigo=c['codigo'])
        for campo in campos:
            setattr(sede, campo, c.get(campo))
        db.session.add(sede)
    db.session.commit()
    return SedeEducativa.query.count()


def _plano(texto):
    return re.sub(r'[^A-Z0-9 ]', ' ', sin_tildes(texto or '').upper())


def sector_canonico(valor):
    """"público" y "oficial" son lo mismo en el catálogo. Devuelve None si no se reconoce."""
    return SECTORES.get(sin_tildes(valor or '').strip().upper())


def buscar_colegios(consulta, municipio=None, sector=None, limite=12):
    """Busca por palabras sueltas en el nombre o la sede ("javiera", "ie san jose bello").

    Sin texto escrito pero con sector (o municipio) devuelve la lista completa de ese
    grupo, que es lo que se despliega en el registro cuando el estudiante responde si
    su colegio es público o privado.
    """
    palabras = [p for p in _plano(consulta).split() if len(p) >= 2]
    sec = sector_canonico(sector)
    mpio = municipio_canonico(municipio)
    if not palabras and not sec and not mpio:
        return []
    q = SedeEducativa.query
    if sec:
        q = q.filter(SedeEducativa.sector == sec)
    if mpio:
        q = q.filter(SedeEducativa.municipio == mpio)
    # Se busca en el nombre del catálogo y en el nombre ya limpio, para que "institución
    # educativa" encuentre también a los que el catálogo abrevia como "IE".
    hallados = [s for s in q.all()
                if all(p in _plano(f'{s.nombre} {s.nombre_limpio} {s.sede} {s.municipio} {s.barrio or ""}')
                       for p in palabras)]
    # Primero los que empiezan por la primera palabra y, dentro de cada colegio, la sede principal.
    empieza = (lambda s: not _plano(s.nombre_limpio).startswith(palabras[0])) if palabras else (lambda s: False)
    hallados.sort(key=lambda s: (empieza(s), s.sede != s.nombre, _plano(s.nombre_limpio), s.sede or ''))
    return [s.to_dict() for s in hallados[:limite]]


def contar_colegios(sector=None, municipio=None):
    """Cuántas sedes hay en ese grupo (para avisar que la lista viene recortada)."""
    q = SedeEducativa.query
    sec = sector_canonico(sector)
    mpio = municipio_canonico(municipio)
    if sec:
        q = q.filter(SedeEducativa.sector == sec)
    if mpio:
        q = q.filter(SedeEducativa.municipio == mpio)
    return q.count()


def perfil_de(usuario_id):
    return PerfilEscolar.query.filter_by(usuario_id=usuario_id).first()


def validar(datos):
    """Revisa los datos escolares antes de crear la cuenta. Lanza ValueError con el mensaje."""
    codigo = (datos.get('sede_codigo') or '').strip()
    if codigo and not SedeEducativa.query.filter_by(codigo=codigo).first():
        raise ValueError('El colegio elegido no está en el catálogo.')
    if datos.get('edad') not in (None, ''):
        try:
            edad = int(datos['edad'])
        except (TypeError, ValueError):
            raise ValueError('La edad debe ser un número.')
        if not EDAD_MIN <= edad <= EDAD_MAX:
            raise ValueError(f'La edad debe estar entre {EDAD_MIN} y {EDAD_MAX} años.')
    if datos.get('direccion') and not municipio_canonico(datos.get('municipio')):
        raise ValueError('Elige el municipio del Valle de Aburrá donde vives.')


def guardar_perfil(usuario_id, datos):
    """Guarda colegio, edad y dirección. La dirección se ubica en el servidor (índice local
    y, si no aparece, OpenStreetMap); si no se encuentra, se guarda solo el texto."""
    validar(datos)
    perfil = perfil_de(usuario_id) or PerfilEscolar(usuario_id=usuario_id)

    if 'sede_codigo' in datos or 'colegio_texto' in datos:
        codigo = (datos.get('sede_codigo') or '').strip() or None
        texto = (datos.get('colegio_texto') or '').strip()[:200] or None
        if codigo:
            sede = SedeEducativa.query.filter_by(codigo=codigo).first()
            perfil.sede_codigo, perfil.colegio_texto, perfil.sector = codigo, None, sede.sector
        elif texto:
            # Colegio escrito a mano: el sector es el que respondió el estudiante, si respondió.
            perfil.sede_codigo, perfil.colegio_texto = None, texto
            perfil.sector = sector_canonico(datos.get('colegio_sector'))

    if datos.get('edad') not in (None, ''):
        perfil.edad = int(datos['edad'])

    direccion = (datos.get('direccion') or '').strip()[:200]
    if direccion:
        mpio = municipio_canonico(datos.get('municipio'))
        ubicada = geocodificador.geocodificar(direccion, mpio)
        perfil.municipio = mpio
        perfil.direccion = direccion
        perfil.direccion_normalizada = ubicada.get('normalizada')
        perfil.complemento = ubicada.get('complemento') or None
        if ubicada['encontrada']:
            perfil.lat, perfil.lon = round(ubicada['lat'], 6), round(ubicada['lon'], 6)
            perfil.precision = ubicada['precision']
            perfil.estrato = ubicada.get('estrato') or geocodificador.estrato_cercano(ubicada['lat'], ubicada['lon'])
        else:
            perfil.lat = perfil.lon = perfil.precision = perfil.estrato = None

    db.session.add(perfil)
    db.session.commit()
    return perfil
