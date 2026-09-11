"""Controlador de auditoría y trazabilidad."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from ..models.auditoria import Auditoria, PoliticaRetencion
from ..extensions import db
from ..utils.decorators import roles_requeridos

auditoria_bp = Blueprint('auditoria', __name__)


@auditoria_bp.route('/logs', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo')
def listar_logs():
    """Listar registros de auditoría con filtros."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    modulo = request.args.get('modulo')
    accion = request.args.get('accion')
    usuario_nombre = request.args.get('usuario_nombre', '').strip()
    rol_usuario = request.args.get('rol_usuario', '').strip()

    from ..models.usuario import Usuario, Rol
    query = Auditoria.query
    if modulo:
        query = query.filter_by(modulo=modulo)
    if accion:
        query = query.filter(Auditoria.accion.ilike(f'%{accion}%'))
    if usuario_nombre or rol_usuario:
        query = query.join(Usuario, Auditoria.usuario_id == Usuario.id)
        if usuario_nombre:
            query = query.filter(
                db.or_(
                    Usuario.nombres.ilike(f'%{usuario_nombre}%'),
                    Usuario.apellidos.ilike(f'%{usuario_nombre}%')
                )
            )
        if rol_usuario:
            query = query.join(Rol, Usuario.rol_id == Rol.id).filter(Rol.nombre == rol_usuario)

    paginacion = query.order_by(Auditoria.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'logs': [l.to_dict() for l in paginacion.items],
        'total': paginacion.total,
        'paginas': paginacion.pages,
        'pagina_actual': page,
    }), 200


@auditoria_bp.route('/politicas', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo')
def listar_politicas():
    """Listar políticas de retención de datos."""
    politicas = PoliticaRetencion.query.all()
    return jsonify({'politicas': [p.to_dict() for p in politicas]}), 200


@auditoria_bp.route('/politicas', methods=['POST'])
@jwt_required()
@roles_requeridos('ti')
def crear_politica():
    """Crear una política de retención de datos."""
    from flask_jwt_extended import get_jwt_identity
    datos = request.get_json()

    politica = PoliticaRetencion(
        nombre=datos['nombre'],
        descripcion=datos.get('descripcion'),
        tiempo_retencion_dias=datos['tiempo_retencion_dias'],
        tabla_afectada=datos['tabla_afectada'],
        creado_por=int(get_jwt_identity()),
    )
    db.session.add(politica)
    db.session.commit()

    return jsonify({
        'message': 'Política creada',
        'politica': politica.to_dict()
    }), 201
