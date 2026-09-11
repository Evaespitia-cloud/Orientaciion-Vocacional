"""
Pruebas Unitarias — AuthService
Testea el hashing de contraseñas, validación de credenciales y registro de usuarios
sin necesidad de servidor HTTP activo (usa base de datos en memoria SQLite).
"""

import pytest
import sys
import os
import time

# Definir la base de pruebas antes de importar la configuración de Flask.
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['JWT_SECRET_KEY'] = 'test-secret'

# Asegurar que el paquete 'app' sea importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from app.extensions import db as _db
from app.services.auth_service import AuthService
from app.models.usuario import Rol, Usuario


# ─── Fixture de aplicación con BD en memoria ──────────────────────────────────
@pytest.fixture()
def app():
    app = create_app('development')
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        _db.create_all()
        # Cada prueba recibe una base SQLite nueva y roles mínimos.
        for nombre, desc in [('estudiante', 'Estudiante del sistema'), ('ti', 'Administrador TI')]:
            _db.session.add(Rol(nombre=nombre, descripcion=desc))
        _db.session.commit()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def ctx(app):
    with app.app_context():
        yield


# ─── UT-01: Hash de contraseña ─────────────────────────────────────────────────
class TestHashPassword:
    def test_hash_genera_string_diferente(self, app):
        with app.app_context():
            pwd = 'MiClave123*'
            hashed = AuthService.hash_password(pwd)
            assert hashed != pwd

    def test_hash_no_es_texto_plano(self, app):
        with app.app_context():
            hashed = AuthService.hash_password('Clave123*')
            assert '$2b$' in hashed  # prefijo bcrypt

    def test_verificacion_correcta(self, app):
        with app.app_context():
            pwd = 'Clave123*'
            hashed = AuthService.hash_password(pwd)
            assert AuthService.verify_password(pwd, hashed) is True

    def test_verificacion_incorrecta(self, app):
        with app.app_context():
            hashed = AuthService.hash_password('Clave123*')
            assert AuthService.verify_password('OtraClave', hashed) is False

    def test_hashes_distintos_misma_clave(self, app):
        """bcrypt genera salt distinto cada vez — dos hashes de la misma clave deben diferir."""
        with app.app_context():
            h1 = AuthService.hash_password('Igual123*')
            h2 = AuthService.hash_password('Igual123*')
            assert h1 != h2


# ─── UT-02: Registro de usuario ───────────────────────────────────────────────
class TestRegistroUsuario:
    def test_registro_exitoso(self, app):
        with app.app_context():
            email = f'unit_test_{int(time.time())}@test.com'
            datos = {
                'email': email,
                'password': 'Test1234*',
                'nombres': 'Juan',
                'apellidos': 'Prueba',
            }
            u = AuthService.registrar_usuario(datos)
            assert u.id is not None
            assert u.email == email
            assert u.password_hash != 'Test1234*'

    def test_registro_estudiante_sin_password(self, app):
        with app.app_context():
            email = f'estudiante_sin_password_{int(time.time())}@test.com'
            datos = {
                'email': email,
                'nombres': 'Estudiante',
                'apellidos': 'SinClave',
                'rol': 'estudiante',
            }
            u = AuthService.registrar_usuario(datos)
            assert u.id is not None
            assert u.email == email
            assert u.rol.nombre == 'estudiante'
            assert u.password_hash

    def test_login_estudiante_sin_password(self, app):
        with app.app_context():
            email = f'estudiante_login_sin_password_{int(time.time())}@test.com'
            AuthService.registrar_usuario({
                'email': email,
                'nombres': 'Estudiante',
                'apellidos': 'SinClave',
                'rol': 'estudiante',
            })
            u = AuthService.autenticar(email, '')
            assert u.email == email

    def test_registro_email_duplicado(self, app):
        with app.app_context():
            email = f'duplicado_{int(time.time())}@test.com'
            datos = {
                'email': email,
                'password': 'Test1234*',
                'nombres': 'A',
                'apellidos': 'B',
            }
            AuthService.registrar_usuario(datos)
            with pytest.raises(ValueError, match='ya está registrado'):
                AuthService.registrar_usuario(datos)

    def test_registro_rol_invalido(self, app):
        with app.app_context():
            datos = {
                'email': 'rolmal@test.com',
                'password': 'Test1234*',
                'nombres': 'X',
                'apellidos': 'Y',
                'rol': 'rol_inexistente',
            }
            with pytest.raises(ValueError, match='no encontrado'):
                AuthService.registrar_usuario(datos)


# ─── UT-03: Autenticación ─────────────────────────────────────────────────────
class TestAutenticacion:
    def test_login_exitoso(self, app):
        with app.app_context():
            AuthService.registrar_usuario({
                'email': 'login_ok@test.com',
                'password': 'Login123*',
                'nombres': 'Login',
                'apellidos': 'Test',
            })
            u = AuthService.autenticar('login_ok@test.com', 'Login123*')
            assert u.email == 'login_ok@test.com'

    def test_login_email_incorrecto(self, app):
        with app.app_context():
            with pytest.raises(ValueError, match='Credenciales'):
                AuthService.autenticar('noexiste@test.com', 'cualquier')

    def test_login_password_incorrecto(self, app):
        with app.app_context():
            AuthService.registrar_usuario({
                'email': 'pwdmal@test.com',
                'password': 'Correcto123*',
                'nombres': 'P',
                'apellidos': 'Q',
            })
            with pytest.raises(ValueError, match='Credenciales'):
                AuthService.autenticar('pwdmal@test.com', 'Incorrecta999')

    def test_login_usuario_inactivo(self, app):
        with app.app_context():
            u = AuthService.registrar_usuario({
                'email': 'inactivo@test.com',
                'password': 'Inact123*',
                'nombres': 'I',
                'apellidos': 'N',
            })
            u.activo = False
            _db.session.commit()
            with pytest.raises(ValueError, match='inactiva'):
                AuthService.autenticar('inactivo@test.com', 'Inact123*')
