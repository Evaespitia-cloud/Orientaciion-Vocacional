"""Controlador de configuración de aplicación del instrumento."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from ..extensions import db
from ..models.aplicacion import ConfiguracionAplicacion
from ..utils.decorators import roles_requeridos
from ..utils.audit import registrar_auditoria

config_bp = Blueprint('configuracion', __name__)


@config_bp.route('/', methods=['GET'])
@jwt_required()
def listar_configuraciones():
    """Listar configuraciones de aplicación."""
    activa = request.args.get('activa', type=str)
    query = ConfiguracionAplicacion.query

    if activa is not None:
        query = query.filter_by(activa=activa.lower() == 'true')

    configs = query.order_by(ConfiguracionAplicacion.created_at.desc()).all()
    return jsonify({'configuraciones': [c.to_dict() for c in configs]}), 200


@config_bp.route('/', methods=['POST'])
@jwt_required()
@roles_requeridos('bienestar', 'ti')
def crear_configuracion():
    """Crear una nueva configuración de aplicación."""
    datos = request.get_json()
    usuario_id = int(get_jwt_identity())

    campos_requeridos = ['instrumento_id', 'nombre', 'fecha_inicio', 'fecha_fin']
    for campo in campos_requeridos:
        if campo not in datos:
            return jsonify({'error': f'El campo "{campo}" es requerido'}), 400

    try:
        config = ConfiguracionAplicacion(
            instrumento_id=datos['instrumento_id'],
            nombre=datos['nombre'],
            descripcion=datos.get('descripcion'),
            fecha_inicio=datetime.fromisoformat(datos['fecha_inicio']),
            fecha_fin=datetime.fromisoformat(datos['fecha_fin']),
            obligatoria=datos.get('obligatoria', False),
            institucion_id=datos.get('institucion_id'),
            grado_id=datos.get('grado_id'),
            cohorte=datos.get('cohorte'),
            creado_por=usuario_id,
        )
        db.session.add(config)
        db.session.commit()

        registrar_auditoria(
            usuario_id, 'CREAR_CONFIGURACION', 'configuracion',
            f'Configuración "{config.nombre}" creada',
            ip_address=request.remote_addr
        )

        return jsonify({
            'message': 'Configuración creada',
            'configuracion': config.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@config_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def obtener_configuracion(id):
    """Obtener una configuración específica."""
    config = ConfiguracionAplicacion.query.get_or_404(id)
    return jsonify({'configuracion': config.to_dict()}), 200


@config_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
@roles_requeridos('bienestar', 'ti')
def actualizar_configuracion(id):
    """Actualizar una configuración de aplicación."""
    config = ConfiguracionAplicacion.query.get_or_404(id)
    datos = request.get_json()

    if 'nombre' in datos:
        config.nombre = datos['nombre']
    if 'descripcion' in datos:
        config.descripcion = datos['descripcion']
    if 'fecha_inicio' in datos:
        config.fecha_inicio = datetime.fromisoformat(datos['fecha_inicio'])
    if 'fecha_fin' in datos:
        config.fecha_fin = datetime.fromisoformat(datos['fecha_fin'])
    if 'obligatoria' in datos:
        config.obligatoria = datos['obligatoria']
    if 'activa' in datos:
        config.activa = datos['activa']
    if 'institucion_id' in datos:
        config.institucion_id = datos['institucion_id']
    if 'grado_id' in datos:
        config.grado_id = datos['grado_id']
    if 'cohorte' in datos:
        config.cohorte = datos['cohorte']

    db.session.commit()

    registrar_auditoria(
        int(get_jwt_identity()), 'ACTUALIZAR_CONFIGURACION', 'configuracion',
        f'Configuración "{config.nombre}" actualizada',
        ip_address=request.remote_addr
    )

    return jsonify({
        'message': 'Configuración actualizada',
        'configuracion': config.to_dict()
    }), 200
