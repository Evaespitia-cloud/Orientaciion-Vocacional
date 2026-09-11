"""
Pruebas de Integración — API REST
Testea los endpoints HTTP contra el servidor real en localhost:5000
Requiere que el backend esté corriendo con datos de seed disponibles.
"""

import pytest
import requests

BASE = 'http://localhost:5000/api'

# ─── Credenciales de prueba ────────────────────────────────────────────────────
ADMIN_TI   = {'email': 'admin@orientacion.edu.co',   'password': 'Admin123*'}
BIENESTAR  = {'email': 'bienestar@orientacion.edu.co', 'password': 'Bienestar123*'}
ESTUDIANTE_CREDS = {'email': 'sanny@orientacion.edu.co', 'password': 'Sanny123*'}

EMAIL_NUEVO = 'integ_test_nuevo@test.com'


def get_token(creds):
    r = requests.post(f'{BASE}/auth/login', json=creds)
    return r.json().get('access_token', '')

def auth_header(token):
    return {'Authorization': f'Bearer {token}'}


# ─── IT-01: Autenticación ─────────────────────────────────────────────────────
class TestAutenticacionAPI:
    def test_login_exitoso_admin(self):
        r = requests.post(f'{BASE}/auth/login', json=ADMIN_TI)
        assert r.status_code == 200
        data = r.json()
        assert 'access_token' in data
        assert data['usuario']['rol']['nombre'] in ('ti', 'bienestar', 'directivo')

    def test_login_credenciales_invalidas(self):
        r = requests.post(f'{BASE}/auth/login', json={
            'email': 'noexiste@test.com', 'password': 'MalaClave1'
        })
        assert r.status_code == 401

    def test_login_sin_body(self):
        r = requests.post(f'{BASE}/auth/login', json={})
        assert r.status_code == 400

    def test_login_password_faltante(self):
        r = requests.post(f'{BASE}/auth/login', json={'email': 'admin@orientacion.edu.co'})
        assert r.status_code == 400

    def test_token_verify_valido(self):
        token = get_token(ADMIN_TI)
        r = requests.get(f'{BASE}/auth/verify', headers=auth_header(token))
        assert r.status_code == 200

    def test_token_invalido_rechazado(self):
        r = requests.get(f'{BASE}/auth/verify', headers=auth_header('token.falso.invalido'))
        assert r.status_code == 422

    def test_health_check(self):
        r = requests.get(f'{BASE}/health')
        assert r.status_code == 200
        assert r.json().get('status') == 'ok'


# ─── IT-02: Registro ──────────────────────────────────────────────────────────
class TestRegistroAPI:
    def test_registro_exitoso(self):
        import time
        email = f'regtest_{int(time.time())}@test.com'
        r = requests.post(f'{BASE}/auth/registro', json={
            'email': email,
            'password': 'Registro123*',
            'nombres': 'Prueba',
            'apellidos': 'Integracion',
        })
        assert r.status_code == 201
        assert r.json().get('usuario', {}).get('email') == email

    def test_registro_password_corta(self):
        r = requests.post(f'{BASE}/auth/registro', json={
            'email': 'corta@test.com', 'password': 'abc',
            'nombres': 'A', 'apellidos': 'B',
        })
        assert r.status_code == 400
        assert 'error' in r.json()

    def test_registro_password_sin_mayuscula(self):
        r = requests.post(f'{BASE}/auth/registro', json={
            'email': 'sinmay@test.com', 'password': 'sinmayuscula1',
            'nombres': 'A', 'apellidos': 'B',
        })
        assert r.status_code == 400

    def test_registro_password_sin_numero(self):
        r = requests.post(f'{BASE}/auth/registro', json={
            'email': 'sinnum@test.com', 'password': 'SinNumero',
            'nombres': 'A', 'apellidos': 'B',
        })
        assert r.status_code == 400

    def test_registro_campos_faltantes(self):
        r = requests.post(f'{BASE}/auth/registro', json={
            'email': 'incompleto@test.com',
        })
        assert r.status_code == 400


# ─── IT-03: Usuarios ──────────────────────────────────────────────────────────
class TestUsuariosAPI:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token_ti = get_token(ADMIN_TI)

    def test_listar_usuarios_como_ti(self):
        r = requests.get(f'{BASE}/usuarios/', headers=auth_header(self.token_ti))
        assert r.status_code == 200
        data = r.json()
        assert 'usuarios' in data
        assert 'total' in data

    def test_listar_usuarios_sin_token(self):
        r = requests.get(f'{BASE}/usuarios/')
        assert r.status_code == 401

    def test_listar_usuarios_token_invalido(self):
        r = requests.get(f'{BASE}/usuarios/', headers=auth_header('invalido'))
        assert r.status_code == 422

    def test_buscar_por_nombre(self):
        r = requests.get(f'{BASE}/usuarios/', headers=auth_header(self.token_ti),
                         params={'buscar': 'Carlos'})
        assert r.status_code == 200
        usuarios = r.json().get('usuarios', [])
        for u in usuarios:
            nombre_completo = (u.get('nombres', '') + ' ' + u.get('apellidos', '')).lower()
            assert 'carlos' in nombre_completo or 'carlos' in u.get('email', '').lower()

    def test_filtrar_por_rol(self):
        r = requests.get(f'{BASE}/usuarios/', headers=auth_header(self.token_ti),
                         params={'rol': 'estudiante'})
        assert r.status_code == 200
        for u in r.json().get('usuarios', []):
            assert u['rol']['nombre'] == 'estudiante'

    def test_created_at_presente(self):
        """Verifica que created_at se retorna tras el fix aplicado."""
        r = requests.get(f'{BASE}/usuarios/', headers=auth_header(self.token_ti))
        assert r.status_code == 200
        for u in r.json().get('usuarios', []):
            assert 'created_at' in u  # campo fue añadido al to_dict()

    def test_crear_usuario_como_ti(self):
        import time
        email = f'creado_api_{int(time.time())}@test.com'
        r = requests.post(f'{BASE}/usuarios/', headers=auth_header(self.token_ti), json={
            'email': email,
            'password': 'Nuevo123*',
            'nombres': 'Creado',
            'apellidos': 'PorAPI',
            'rol': 'estudiante',
        })
        assert r.status_code == 201
        assert r.json().get('usuario', {}).get('email') == email

    def test_crear_usuario_rol_invalido(self):
        r = requests.post(f'{BASE}/usuarios/', headers=auth_header(self.token_ti), json={
            'email': 'rolmal@test.com', 'password': 'Clave123*',
            'nombres': 'X', 'apellidos': 'Y', 'rol': 'superadmin_inexistente',
        })
        assert r.status_code in (400, 404)

    def test_obtener_usuario_por_id(self):
        # Obtener primer usuario de la lista
        lista = requests.get(f'{BASE}/usuarios/', headers=auth_header(self.token_ti)).json()
        uid = lista['usuarios'][0]['id']
        r = requests.get(f'{BASE}/usuarios/{uid}', headers=auth_header(self.token_ti))
        assert r.status_code == 200
        assert r.json().get('usuario', {}).get('id') == uid


# ─── IT-04: RBAC — Control de acceso por roles ────────────────────────────────
class TestRBAC:
    def test_estudiante_no_puede_listar_usuarios(self):
        """Un estudiante no debe poder acceder a la lista de usuarios."""
        token = get_token(ESTUDIANTE_CREDS)
        if not token:
            pytest.skip('Credenciales de estudiante no disponibles en seed')
        r = requests.get(f'{BASE}/usuarios/', headers=auth_header(token))
        assert r.status_code == 403

    def test_sin_token_no_puede_listar_usuarios(self):
        r = requests.get(f'{BASE}/usuarios/')
        assert r.status_code == 401

    def test_estudiante_no_puede_crear_usuario(self):
        token = get_token(ESTUDIANTE_CREDS)
        if not token:
            pytest.skip('Credenciales de estudiante no disponibles')
        r = requests.post(f'{BASE}/usuarios/', headers=auth_header(token), json={
            'email': 'rbactest@test.com', 'password': 'Rbac123*',
            'nombres': 'R', 'apellidos': 'B', 'rol': 'estudiante',
        })
        assert r.status_code == 403

    def test_endpoint_formulas_requiere_rol(self):
        """Formulas de cálculo solo accesibles para bienestar y ti."""
        token = get_token(ESTUDIANTE_CREDS)
        if not token:
            pytest.skip('No hay token de estudiante')
        r = requests.get(f'{BASE}/demografico/formulas', headers=auth_header(token))
        assert r.status_code == 403


# ─── IT-05: Instrumentos ──────────────────────────────────────────────────────
class TestInstrumentosAPI:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = get_token(ADMIN_TI)

    def test_listar_instrumentos(self):
        r = requests.get(f'{BASE}/instrumentos/', headers=auth_header(self.token))
        assert r.status_code == 200
        assert 'instrumentos' in r.json()

    def test_instrumento_tiene_dimensiones(self):
        lista = requests.get(f'{BASE}/instrumentos/', headers=auth_header(self.token)).json()
        if not lista['instrumentos']:
            pytest.skip('No hay instrumentos en BD')
        iid = lista['instrumentos'][0]['id']
        r = requests.get(f'{BASE}/instrumentos/{iid}', headers=auth_header(self.token))
        assert r.status_code == 200
        inst = r.json().get('instrumento', {})
        assert 'dimensiones' in inst


# ─── IT-06: Campos y fórmulas demográficas ───────────────────────────────────
class TestDemograficoAPI:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = get_token(ADMIN_TI)

    def test_listar_campos(self):
        r = requests.get(f'{BASE}/demografico/campos', headers=auth_header(self.token))
        assert r.status_code == 200
        assert 'campos' in r.json()

    def test_listar_formulas(self):
        r = requests.get(f'{BASE}/demografico/formulas', headers=auth_header(self.token))
        assert r.status_code == 200
        assert 'formulas' in r.json()

    def test_crear_formula_json(self):
        import time
        r = requests.post(f'{BASE}/demografico/formulas', headers=auth_header(self.token), json={
            'nombre': f'Formula Test {int(time.time())}',
            'descripcion': 'Prueba integración',
            'tipo': 'holland_riasec',
            'parametros': {
                '_formato': 'json',
                'metodo': 'suma_binaria',
                'valor_positivo': 1,
                'valor_negativo': 0,
            },
        })
        assert r.status_code == 201
        assert r.json().get('formula', {}).get('nombre') is not None


# ─── IT-07: Auditoría ─────────────────────────────────────────────────────────
class TestAuditoriaAPI:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = get_token(ADMIN_TI)

    def test_listar_logs(self):
        r = requests.get(f'{BASE}/auditoria/logs', headers=auth_header(self.token))
        assert r.status_code == 200
        assert 'logs' in r.json()

    def test_filtrar_logs_por_modulo(self):
        r = requests.get(f'{BASE}/auditoria/logs', headers=auth_header(self.token),
                         params={'modulo': 'auth'})
        assert r.status_code == 200
        for log in r.json().get('logs', []):
            assert log.get('modulo') == 'auth'

    def test_listar_politicas(self):
        r = requests.get(f'{BASE}/auditoria/politicas', headers=auth_header(self.token))
        assert r.status_code == 200


# ─── IT-08: Estadísticas ──────────────────────────────────────────────────────
class TestEstadisticasAPI:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = get_token(ADMIN_TI)

    def test_resumen(self):
        r = requests.get(f'{BASE}/estadisticas/resumen', headers=auth_header(self.token))
        assert r.status_code == 200

    def test_distribucion_perfiles(self):
        r = requests.get(f'{BASE}/estadisticas/perfiles', headers=auth_header(self.token))
        assert r.status_code == 200


# ─── IT-09: Exportación ───────────────────────────────────────────────────────
class TestExportacionAPI:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = get_token(ADMIN_TI)

    def test_exportar_csv_estadisticas(self):
        r = requests.get(f'{BASE}/exportacion/csv/estadisticas', headers=auth_header(self.token))
        assert r.status_code == 200
        assert 'csv' in r.headers.get('Content-Type', '').lower() or \
               'text' in r.headers.get('Content-Type', '').lower()

    def test_exportar_csv_resultados_anonimizado(self):
        r = requests.get(f'{BASE}/exportacion/csv/resultados',
                         headers=auth_header(self.token),
                         params={'anonimizado': 'true'})
        assert r.status_code == 200
