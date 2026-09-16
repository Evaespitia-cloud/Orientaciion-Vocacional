"""Servicio de autenticación — hashing, JWT, validación."""

import bcrypt
from datetime import datetime
from ..extensions import db
from ..models.usuario import Usuario, Rol
import re


class AuthService:
    """Servicio para operaciones de autenticación."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Genera hash seguro de contraseña."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verifica contraseña contra hash."""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

    @staticmethod
    def validar_password(password: str) -> None:
        """Política mínima de contraseña para cuentas nuevas o cambios de clave."""
        if len(password or '') < 10:
            raise ValueError('La contraseña debe tener al menos 10 caracteres')
        if not re.search(r'[A-Z]', password):
            raise ValueError('La contraseña debe contener al menos una letra mayúscula')
        if not re.search(r'[a-z]', password):
            raise ValueError('La contraseña debe contener al menos una letra minúscula')
        if not re.search(r'\d', password):
            raise ValueError('La contraseña debe contener al menos un número')
        if not re.search(r'[^A-Za-z0-9]', password):
            raise ValueError('La contraseña debe contener al menos un carácter especial')

    @staticmethod
    def _password_para_registro(datos: dict, rol_nombre: str) -> str:
        """Todos los usuarios deben definir una contraseña propia."""
        password = str(datos.get('password') or '')
        if not password:
            raise ValueError('La contraseña es requerida')
        AuthService.validar_password(password)
        return password

    @staticmethod
    def registrar_usuario(datos: dict) -> Usuario:
        """Registra un nuevo usuario en el sistema."""
        email = str(datos.get('email') or '').strip().lower()
        if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email) or len(email) > 255:
            raise ValueError('Correo electrónico inválido')
        datos['email'] = email

        # Verificar que el email no exista
        if Usuario.query.filter_by(email=email).first():
            raise ValueError('El correo electrónico ya está registrado')

        # Documento y teléfono vacíos se guardan como NULL: '' rompería la
        # restricción UNIQUE de documento en el segundo registro sin documento.
        documento = str(datos.get('documento') or '').strip() or None
        datos['documento'] = documento
        datos['telefono'] = str(datos.get('telefono') or '').strip() or None
        if documento and Usuario.query.filter_by(documento=documento).first():
            raise ValueError('El documento ya está registrado')

        # Obtener rol (por defecto estudiante)
        rol_nombre = (datos.get('rol') or 'estudiante').strip().lower()
        rol = Rol.query.filter_by(nombre=rol_nombre).first()
        if not rol:
            raise ValueError(f'Rol "{rol_nombre}" no encontrado')

        password = AuthService._password_para_registro(datos, rol_nombre)

        usuario = Usuario(
            email=datos['email'],
            password_hash=AuthService.hash_password(password),
            nombres=datos['nombres'],
            apellidos=datos['apellidos'],
            documento=datos.get('documento'),
            tipo_documento=datos.get('tipo_documento', 'CC'),
            telefono=datos.get('telefono'),
            rol_id=rol.id,
            grado_id=datos.get('grado_id'),
            semestre=datos.get('semestre'),
            cohorte=datos.get('cohorte'),
        )

        db.session.add(usuario)
        db.session.commit()
        return usuario

    @staticmethod
    def autenticar(email: str, password: str) -> Usuario:
        """Autentica un usuario por email y contraseña.

        Valida exclusivamente la contraseña asociada a la cuenta.
        """
        email_normalizado = (email or '').strip().lower()
        usuario = Usuario.query.filter_by(email=email_normalizado).first()
        if not usuario:
            raise ValueError('Credenciales inválidas')

        password_real = password or ''
        password_valida = AuthService.verify_password(password_real, usuario.password_hash)


        if not password_valida:
            raise ValueError('Credenciales inválidas')

        if not usuario.activo:
            raise ValueError('Cuenta inactiva')

        # Actualizar último acceso
        usuario.ultimo_acceso = datetime.utcnow()
        db.session.commit()

        return usuario
