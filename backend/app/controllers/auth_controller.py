"""Controlador de autenticación — login, registro, logout."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity, get_jwt
)
from ..services.auth_service import AuthService
from ..extensions import db
from ..utils.audit import registrar_auditoria
from ..utils.rate_limit import allow_request

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/grados', methods=['GET'])
def listar_grados():
    """Listar grados disponibles (endpoint público para el registro)."""
    from ..models.institucional import Grado
    grados = Grado.query.filter_by(activo=True).order_by(Grado.nombre).all()
    return jsonify({'grados': [g.to_dict() for g in grados]}), 200


@auth_bp.route('/registro', methods=['POST'])
def registro():
    """Registrar un nuevo usuario.

    El registro público siempre crea estudiantes y exige una contraseña propia
    que cumpla la política de seguridad definida por AuthService.
    """
    datos = request.get_json(silent=True) or {}

    campos_requeridos = ['email', 'nombres', 'apellidos']
    for campo in campos_requeridos:
        if not datos.get(campo):
            return jsonify({'error': f'El campo "{campo}" es requerido'}), 400

    # El endpoint público nunca puede crear roles privilegiados.
    datos['rol'] = 'estudiante'
    if not allow_request(f"registro:{request.remote_addr}", 5, 600):
        return jsonify({'error': 'Demasiados intentos de registro. Intenta nuevamente más tarde.'}), 429
    password = str(datos.get('password') or '')
    try:
        AuthService.validar_password(password)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    try:
        usuario = AuthService.registrar_usuario(datos)
        registrar_auditoria(
            usuario.id, 'REGISTRO', 'auth',
            f'Nuevo usuario registrado: {usuario.email}',
            ip_address=request.remote_addr
        )
        return jsonify({
            'message': 'Usuario registrado exitosamente',
            'usuario': usuario.to_dict()
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception:
        return jsonify({'error': 'Error interno del servidor'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """Iniciar sesión y obtener token JWT."""
    datos = request.get_json(silent=True)

    if not datos or 'email' not in datos or 'password' not in datos:
        return jsonify({'error': 'Email y contraseña son requeridos'}), 400

    email = str(datos.get('email', '')).strip().lower()
    password = str(datos.get('password', ''))

    if not allow_request(f"login:{request.remote_addr}:{email}", 10, 300):
        return jsonify({'error': 'Demasiados intentos de inicio de sesión. Intenta nuevamente en unos minutos.'}), 429

    try:
        usuario = AuthService.autenticar(email, password)
        rol_nombre = usuario.rol.nombre if usuario.rol else None
        access_token = create_access_token(
            identity=str(usuario.id),
            additional_claims={
                'rol': rol_nombre,
                'email': usuario.email,
                'nombre': f'{usuario.nombres} {usuario.apellidos}',
            }
        )
        registrar_auditoria(
            usuario.id, 'LOGIN', 'auth',
            f'Inicio de sesión: {usuario.email}',
            ip_address=request.remote_addr
        )
        return jsonify({
            'access_token': access_token,
            'usuario': usuario.to_dict(),
        }), 200
    except UnicodeError as e:
        # Evita que una codificación corrupta convierta el flujo en un HTML de depuración.
        registrar_auditoria(
            None, 'LOGIN_FALLIDO', 'auth',
            f'Error de decodificación al intentar login para: {email or "desconocido"}',
            ip_address=request.remote_addr
        )
        return jsonify({'error': 'Error de codificación en los datos del usuario. Contacte al administrador.'}), 500
    except ValueError as e:
        # Auditar intento fallido sin usuario_id conocido
        registrar_auditoria(
            None, 'LOGIN_FALLIDO', 'auth',
            f'Intento fallido para: {email or "desconocido"}',
            ip_address=request.remote_addr
        )
        return jsonify({'error': str(e)}), 401
    except Exception:
        return jsonify({'error': 'Error interno del servidor'}), 500


@auth_bp.route('/perfil', methods=['GET'])
@jwt_required()
def perfil():
    """Obtener perfil del usuario autenticado."""
    from ..models.usuario import Usuario
    usuario_id = int(get_jwt_identity())
    usuario = Usuario.query.get_or_404(usuario_id)
    return jsonify({'usuario': usuario.to_dict()}), 200


@auth_bp.route('/perfil', methods=['PUT'])
@jwt_required()
def actualizar_perfil():
    """Actualizar datos del perfil propio (nombres, apellidos, telefono, password)."""
    from ..models.usuario import Usuario
    usuario_id = int(get_jwt_identity())
    usuario = Usuario.query.get_or_404(usuario_id)
    data = request.get_json() or {}

    if 'nombres' in data and data['nombres'].strip():
        usuario.nombres = data['nombres'].strip()
    if 'apellidos' in data and data['apellidos'].strip():
        usuario.apellidos = data['apellidos'].strip()
    if 'telefono' in data:
        usuario.telefono = data['telefono'].strip() or None

    if 'password_actual' in data and 'password_nueva' in data:
        pwd_actual = data['password_actual']
        pwd_nueva = data['password_nueva']
        if not AuthService.verify_password(pwd_actual, usuario.password_hash):
            return jsonify({'error': 'La contraseña actual es incorrecta'}), 400
        try:
            AuthService.validar_password(pwd_nueva)
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400
        usuario.password_hash = AuthService.hash_password(pwd_nueva)

    db.session.commit()
    registrar_auditoria(usuario_id, 'ACTUALIZAR_PERFIL', 'auth', ip_address=request.remote_addr)
    return jsonify({'message': 'Perfil actualizado correctamente', 'usuario': usuario.to_dict()}), 200


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Cerrar sesión."""
    usuario_id = int(get_jwt_identity())
    registrar_auditoria(
        usuario_id, 'LOGOUT', 'auth',
        ip_address=request.remote_addr
    )
    return jsonify({'message': 'Sesión cerrada exitosamente'}), 200


@auth_bp.route('/verify', methods=['GET'])
@jwt_required()
def verify_token():
    """Verificar si el token JWT sigue siendo válido."""
    return jsonify({'valid': True}), 200
