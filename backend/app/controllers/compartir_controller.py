"""Cartas para compartir el resultado: la propia (con nombre opcional) y la pública por enlace."""

from functools import lru_cache

from flask import Blueprint, Response, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..models.aplicacion import Aplicacion
from ..models.resultado import PerfilVocacional
from ..models.usuario import Usuario
from ..services import tarjeta_service
from ..services.analitica.datos import porcentajes_por_area
from ..utils.rate_limit import allow_request, ip_cliente

compartir_bp = Blueprint('compartir', __name__)

# Seis cartas de ejemplo para la portada, una por perfil (porcentajes ilustrativos).
EJEMPLOS = [
    ('RIC', {'Realista': 78, 'Investigador': 66, 'Artístico': 31, 'Social': 40, 'Emprendedor': 45, 'Convencional': 58}),
    ('IAR', {'Realista': 52, 'Investigador': 81, 'Artístico': 60, 'Social': 47, 'Emprendedor': 35, 'Convencional': 44}),
    ('ASE', {'Realista': 30, 'Investigador': 48, 'Artístico': 84, 'Social': 63, 'Emprendedor': 55, 'Convencional': 27}),
    ('SEA', {'Realista': 33, 'Investigador': 42, 'Artístico': 58, 'Social': 82, 'Emprendedor': 64, 'Convencional': 46}),
    ('ECS', {'Realista': 41, 'Investigador': 39, 'Artístico': 44, 'Social': 61, 'Emprendedor': 79, 'Convencional': 65}),
    ('CER', {'Realista': 56, 'Investigador': 50, 'Artístico': 25, 'Social': 43, 'Emprendedor': 62, 'Convencional': 80}),
]


def _imagen(datos, max_edad=0):
    r = Response(datos, mimetype='image/png')
    r.headers['Cache-Control'] = f'public, max-age={max_edad}' if max_edad else 'no-store'
    return r


def _resultado_del_estudiante(usuario_id, aplicacion_id):
    """El perfil más completo del estudiante: el último con las dos pruebas o, si no, el pedido."""
    app = Aplicacion.query.get(aplicacion_id)
    if not app or app.usuario_id != usuario_id:
        return None
    perfiles = (PerfilVocacional.query.join(Aplicacion, PerfilVocacional.aplicacion_id == Aplicacion.id)
                .filter(Aplicacion.usuario_id == usuario_id, Aplicacion.estado == 'completada')
                .order_by(Aplicacion.fecha_fin.desc()).all())
    elegido = None
    for p in perfiles:
        interes, competencia, _ = porcentajes_por_area(p.datos_json)
        if len(interes) == 6 and len(competencia) == 6:
            elegido = p
            break
    elegido = elegido or PerfilVocacional.query.filter_by(aplicacion_id=aplicacion_id).first()
    if not elegido:
        return None
    _, _, combinado = porcentajes_por_area(elegido.datos_json)
    codigo = ((elegido.datos_json or {}).get('codigo_riasec') or tarjeta_service.LETRA.get(elegido.perfil_principal, 'R'))[:3]
    return codigo, combinado


@compartir_bp.route('/mio/<int:aplicacion_id>', methods=['GET'])
@jwt_required()
def mio(aplicacion_id):
    datos = _resultado_del_estudiante(int(get_jwt_identity()), aplicacion_id)
    if not datos:
        return jsonify({'error': 'Resultado no encontrado'}), 404
    codigo, porcentajes = datos
    return jsonify({'codigo': tarjeta_service.crear_codigo(codigo, porcentajes)}), 200


@compartir_bp.route('/mio/<int:aplicacion_id>.png', methods=['GET'])
@jwt_required()
def mio_png(aplicacion_id):
    usuario_id = int(get_jwt_identity())
    datos = _resultado_del_estudiante(usuario_id, aplicacion_id)
    if not datos:
        return jsonify({'error': 'Resultado no encontrado'}), 404
    nombre = None
    if request.args.get('nombre') == '1':
        u = Usuario.query.get(usuario_id)
        nombre = (u.nombres or '').split(' ')[0] if u else None
    codigo, porcentajes = datos
    return _imagen(tarjeta_service.png(codigo, porcentajes, request.args.get('formato', 'historia'),
                                       nombre=nombre, sitio=request.args.get('sitio', '')[:60]))


@compartir_bp.route('/ejemplos', methods=['GET'])
def ejemplos():
    return jsonify({'codigos': [tarjeta_service.crear_codigo(c, p) for c, p in EJEMPLOS]}), 200


@compartir_bp.route('/publico/<codigo>', methods=['GET'])
def publico(codigo):
    leido = tarjeta_service.leer_codigo(codigo)
    if not leido:
        return jsonify({'error': 'Enlace no válido'}), 404
    letras, porcentajes = leido
    principal, secundario = tarjeta_service.perfiles_de(letras)
    return jsonify({'codigo_riasec': letras, 'principal': principal, 'secundario': secundario,
                    'porcentajes': porcentajes}), 200


@compartir_bp.route('/publico/<codigo>.png', methods=['GET'])
def publico_png(codigo):
    if not allow_request(f'carta:{ip_cliente()}', 60, 60):
        return jsonify({'error': 'Demasiadas solicitudes'}), 429
    leido = tarjeta_service.leer_codigo(codigo)
    if not leido:
        return jsonify({'error': 'Enlace no válido'}), 404
    letras, porcentajes = leido
    formato = 'enlace' if request.args.get('formato') == 'enlace' else 'historia'
    return _imagen(_png_publico(letras, tuple(porcentajes.items()), formato, request.args.get('sitio', '')[:60]),
                   max_edad=86400)


@lru_cache(maxsize=256)
def _png_publico(letras, porcentajes, formato, sitio):
    """La carta pública solo depende del código firmado: se guarda para no redibujarla
    (en el plan gratuito de Render cada carta cuesta uno o dos segundos de CPU)."""
    return tarjeta_service.png(letras, dict(porcentajes), formato, sitio=sitio)
