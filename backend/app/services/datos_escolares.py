"""Una sola fuente para el colegio, el sector, la edad y el grado de cada estudiante.

Primero se lee la tabla ``perfiles_escolares`` y el grado del registro
(``usuarios.semestre``, que guarda 9, 10 u 11). Si un estudiante no tiene esos
datos, se usan los campos demográficos que algunas instalaciones configuraron a
mano (``nombre_colegio``, ``tipo_colegio``, ``edad`` y ``grado_escolar``).
"""

from ..extensions import db
from ..models.demografico import CampoDemografico, DatoDemografico
from ..models.escolar import PerfilEscolar
from ..models.usuario import Usuario

CAMPOS_VIEJOS = {'nombre_colegio': 'colegio', 'tipo_colegio': 'sector', 'edad': 'edad', 'grado_escolar': 'grado'}
RANGOS_EDAD = ['≤14 años', '15 años', '16 años', '17 años', '18 años', '19+ años', 'No especificado']


DOMINIO_SIMULACION = '@simulacion.local'


def es_simulado(email):
    """Las cohortes simuladas (la del Excel y la del Valle) usan este dominio de correo."""
    return bool(email) and email.lower().endswith(DOMINIO_SIMULACION)


def normalizar_grado(valor):
    if valor in (None, ''):
        return None
    txt = str(valor).strip().lower()
    if txt.startswith('9') or 'nov' in txt:
        return '9°'
    if txt.startswith('10') or 'déc' in txt or 'dec' in txt:
        return '10°'
    if txt.startswith('11') or 'once' in txt:
        return '11°'
    return str(valor).strip()


def normalizar_sector(valor):
    if not valor:
        return None
    txt = str(valor).strip().lower()
    if txt.startswith(('ofic', 'públ', 'publ')):
        return 'Oficial'
    if txt.startswith(('priv', 'no ofic')):
        return 'Privado'
    return str(valor).strip()


def rango_edad(valor):
    try:
        e = int(valor)
    except (TypeError, ValueError):
        return 'No especificado'
    if e <= 14:
        return '≤14 años'
    if e >= 19:
        return '19+ años'
    return f'{e} años'


def por_usuario(incluir_simulados=True):
    """{usuario_id: {'colegio', 'sector', 'edad', 'grado', 'municipio', 'estrato', 'simulado'}}."""
    datos = {}
    for u_id, semestre, email in db.session.query(Usuario.id, Usuario.semestre, Usuario.email).all():
        datos[u_id] = {'colegio': None, 'sector': None, 'edad': None, 'grado': normalizar_grado(semestre),
                       'municipio': None, 'estrato': None, 'simulado': es_simulado(email)}

    campos = {c.id: CAMPOS_VIEJOS[c.nombre]
              for c in CampoDemografico.query.filter(CampoDemografico.nombre.in_(CAMPOS_VIEJOS)).all()}
    if campos:
        for d in DatoDemografico.query.filter(DatoDemografico.campo_id.in_(campos)).all():
            fila = datos.get(d.usuario_id)
            clave = campos[d.campo_id]
            if fila is not None and fila[clave] in (None, '') and d.valor not in (None, ''):
                fila[clave] = d.valor

    for p in PerfilEscolar.query.all():
        fila = datos.get(p.usuario_id)
        if fila is None:
            continue
        fila.update({k: v for k, v in {
            'colegio': p.colegio, 'sector': p.sector, 'edad': p.edad,
            'municipio': p.municipio, 'estrato': p.estrato,
        }.items() if v not in (None, '')})
        fila['simulado'] = fila['simulado'] or bool(p.simulado)

    for fila in datos.values():
        fila['grado'] = normalizar_grado(fila['grado'])
        fila['sector'] = normalizar_sector(fila['sector'])
    if not incluir_simulados:
        datos = {k: v for k, v in datos.items() if not v['simulado']}
    return datos
