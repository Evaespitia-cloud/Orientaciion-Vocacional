"""Decoradores para control de acceso basado en roles y permisos."""

from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from ..models.usuario import Usuario


def roles_requeridos(*roles_permitidos):
    """Decorador que restringe acceso a ciertos roles."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            usuario_id = int(get_jwt_identity())
            usuario = Usuario.query.get(usuario_id)

            if not usuario or not usuario.activo:
                return jsonify({'error': 'Usuario no encontrado o inactivo'}), 403

            if usuario.rol.nombre not in roles_permitidos:
                return jsonify({'error': 'No tiene permisos para acceder a este recurso'}), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def permiso_requerido(codigo_permiso):
    """Decorador que verifica un permiso específico."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            usuario_id = int(get_jwt_identity())
            usuario = Usuario.query.get(usuario_id)

            if not usuario or not usuario.activo:
                return jsonify({'error': 'Usuario no encontrado o inactivo'}), 403

            permisos_usuario = [p.codigo for p in usuario.rol.permisos]
            if codigo_permiso not in permisos_usuario:
                return jsonify({'error': 'No tiene el permiso necesario'}), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator
