"""Controlador de gestión de usuarios y roles."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_
from ..extensions import db
from ..models.usuario import Usuario, Rol
from ..utils.decorators import roles_requeridos
from ..utils.audit import registrar_auditoria
from ..services.auth_service import AuthService

usuario_bp = Blueprint('usuarios', __name__)


@usuario_bp.route('/', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo')
def listar_usuarios():
    """Listar todos los usuarios con filtros opcionales."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    rol = request.args.get('rol')
    grado_id = request.args.get('grado_id', type=int)
    activo = request.args.get('activo', type=str)
    buscar = request.args.get('buscar', '').strip()

    query = Usuario.query
    if rol:
        query = query.join(Rol).filter(Rol.nombre == rol)
    if grado_id:
        query = query.filter_by(grado_id=grado_id)
    if activo is not None:
        query = query.filter_by(activo=activo.lower() == 'true')
    if buscar:
        termino = f'%{buscar}%'
        query = query.filter(
            or_(
                Usuario.nombres.ilike(termino),
                Usuario.apellidos.ilike(termino),
                Usuario.email.ilike(termino),
            )
        )

    paginacion = query.order_by(Usuario.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'usuarios': [u.to_dict() for u in paginacion.items],
        'total': paginacion.total,
        'paginas': paginacion.pages,
        'pagina_actual': page,
    }), 200


@usuario_bp.route('/', methods=['POST'])
@jwt_required()
@roles_requeridos('ti')
def crear_usuario():
    """Crear un usuario desde el panel administrativo."""
    datos = request.get_json()
    admin_id = int(get_jwt_identity())

    campos_requeridos = ['email', 'password', 'nombres', 'apellidos', 'rol']
    for campo in campos_requeridos:
        if not datos.get(campo):
            return jsonify({'error': f'El campo "{campo}" es requerido'}), 400

    try:
        AuthService.validar_password(str(datos.get('password') or ''))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    # Verificar rol válido
    rol_obj = Rol.query.filter_by(nombre=datos['rol']).first()
    if not rol_obj:
        return jsonify({'error': f'Rol "{datos["rol"]}" no existe'}), 400

    try:
        usuario = AuthService.registrar_usuario(datos)
        # Asignar rol indicado por el admin (puede diferir del default)
        usuario.rol_id = rol_obj.id
        if 'activo' in datos:
            usuario.activo = datos['activo']
        db.session.commit()

        registrar_auditoria(
            admin_id, 'CREAR_USUARIO', 'usuarios',
            f'Usuario "{usuario.email}" creado con rol "{datos["rol"]}" por administrador',
            ip_address=request.remote_addr
        )
        return jsonify({'message': 'Usuario creado exitosamente', 'usuario': usuario.to_dict()}), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Error interno del servidor'}), 500


@usuario_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def obtener_usuario(id):
    """Obtener un usuario específico."""
    usuario = Usuario.query.get_or_404(id)
    solicitante_id = int(get_jwt_identity())
    solicitante = Usuario.query.get(solicitante_id)
    roles_admin = {'bienestar', 'ti', 'directivo'}
    if solicitante_id != id and (not solicitante or not solicitante.rol or solicitante.rol.nombre not in roles_admin):
        return jsonify({'error': 'No autorizado'}), 403
    return jsonify({'usuario': usuario.to_dict()}), 200


@usuario_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
@roles_requeridos('bienestar', 'ti')
def actualizar_usuario(id):
    """Actualizar datos de un usuario."""
    usuario = Usuario.query.get_or_404(id)
    datos = request.get_json()

    campos_actualizables = ['nombres', 'apellidos', 'email', 'telefono', 'grado_id',
                            'semestre', 'cohorte', 'activo']
    datos_anteriores = usuario.to_dict()

    for campo in campos_actualizables:
        if campo in datos:
            setattr(usuario, campo, datos[campo])

    if 'rol' in datos:
        solicitante = Usuario.query.get(int(get_jwt_identity()))
        if not solicitante or not solicitante.rol or solicitante.rol.nombre != 'ti':
            return jsonify({'error': 'Solo TI puede modificar roles'}), 403
        rol = Rol.query.filter_by(nombre=datos['rol'], activo=True).first()
        if not rol:
            return jsonify({'error': 'Rol inválido o inactivo'}), 400
        usuario.rol_id = rol.id

    db.session.commit()

    registrar_auditoria(
        int(get_jwt_identity()), 'ACTUALIZAR_USUARIO', 'usuarios',
        f'Usuario {usuario.email} actualizado',
        datos_anteriores=datos_anteriores,
        datos_nuevos=usuario.to_dict(),
        ip_address=request.remote_addr
    )

    return jsonify({'message': 'Usuario actualizado', 'usuario': usuario.to_dict()}), 200


@usuario_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
@roles_requeridos('ti')
def eliminar_usuario(id):
    """Desactivar un usuario (soft delete)."""
    usuario = Usuario.query.get_or_404(id)
    usuario.activo = False
    db.session.commit()

    registrar_auditoria(
        int(get_jwt_identity()), 'DESACTIVAR_USUARIO', 'usuarios',
        f'Usuario {usuario.email} desactivado',
        ip_address=request.remote_addr
    )

    return jsonify({'message': 'Usuario desactivado'}), 200


@usuario_bp.route('/roles', methods=['GET'])
@jwt_required()
def listar_roles():
    """Listar todos los roles disponibles."""
    roles = Rol.query.filter_by(activo=True).all()
    return jsonify({'roles': [r.to_dict() for r in roles]}), 200
