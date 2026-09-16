"""Controlador de gestión de usuarios y roles."""

import re

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
    datos = request.get_json() or {}
    admin_id = int(get_jwt_identity())

    # Los campos opcionales vacíos se guardan como NULL (evita choques de unicidad)
    for campo in ('documento', 'telefono', 'cohorte'):
        if not str(datos.get(campo) or '').strip():
            datos[campo] = None
        else:
            datos[campo] = str(datos[campo]).strip()

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
    """Actualizar datos de un usuario (incluido el restablecimiento de contraseña).

    Solo el rol TI puede cambiar el rol o restablecer la contraseña de otra cuenta.
    """
    usuario = Usuario.query.get_or_404(id)
    datos = request.get_json() or {}

    solicitante_id = int(get_jwt_identity())
    solicitante = Usuario.query.get(solicitante_id)
    es_ti = bool(solicitante and solicitante.rol and solicitante.rol.nombre == 'ti')

    datos_anteriores = usuario.to_dict()

    # --- Email: formato y unicidad ---
    if 'email' in datos:
        email = str(datos.get('email') or '').strip().lower()
        if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email) or len(email) > 255:
            return jsonify({'error': 'Correo electrónico inválido'}), 400
        if Usuario.query.filter(Usuario.email == email, Usuario.id != usuario.id).first():
            return jsonify({'error': 'El correo electrónico ya está registrado'}), 400
        usuario.email = email

    # --- Documento: unicidad (vacío = NULL) ---
    if 'documento' in datos:
        documento = str(datos.get('documento') or '').strip() or None
        if documento and Usuario.query.filter(
                Usuario.documento == documento, Usuario.id != usuario.id).first():
            return jsonify({'error': 'El documento ya está registrado'}), 400
        usuario.documento = documento

    campos_actualizables = ['nombres', 'apellidos', 'telefono', 'tipo_documento',
                            'grado_id', 'semestre', 'cohorte', 'activo']
    for campo in campos_actualizables:
        if campo in datos:
            valor = datos[campo]
            if campo in ('telefono', 'cohorte'):
                valor = str(valor or '').strip() or None
            setattr(usuario, campo, valor)

    # --- Rol: solo TI ---
    if 'rol' in datos:
        if not es_ti:
            return jsonify({'error': 'Solo TI puede modificar roles'}), 403
        rol = Rol.query.filter_by(nombre=datos['rol'], activo=True).first()
        if not rol:
            return jsonify({'error': 'Rol inválido o inactivo'}), 400
        usuario.rol_id = rol.id

    # --- Contraseña: solo TI, aplica la misma política que el registro ---
    password_nueva = str(datos.get('password') or '')
    cambio_password = bool(password_nueva)
    if cambio_password:
        if not es_ti:
            return jsonify({'error': 'Solo TI puede restablecer contraseñas'}), 403
        try:
            AuthService.validar_password(password_nueva)
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400
        usuario.password_hash = AuthService.hash_password(password_nueva)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'No se pudo actualizar el usuario'}), 500

    registrar_auditoria(
        solicitante_id, 'ACTUALIZAR_USUARIO', 'usuarios',
        f'Usuario {usuario.email} actualizado',
        datos_anteriores=datos_anteriores,
        datos_nuevos=usuario.to_dict(),
        ip_address=request.remote_addr
    )

    # La contraseña nunca se registra en auditoría, solo el hecho del cambio
    if cambio_password:
        registrar_auditoria(
            solicitante_id, 'RESTABLECER_PASSWORD', 'usuarios',
            f'Contraseña del usuario {usuario.email} restablecida por un administrador',
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
