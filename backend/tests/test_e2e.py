"""
Pruebas E2E — Flujos completos de usuario
Simula los flujos reales de cada rol desde el primer endpoint hasta el resultado final.
Requiere backend en localhost:5000 con seed completo.
"""

import pytest
import requests
import time

BASE = 'http://localhost:5000/api'
BASE_FRONT = 'http://localhost:5001'

ADMIN_TI = {'email': 'admin@orientacion.edu.co', 'password': 'Admin123*'}

def get_token(creds):
    r = requests.post(f'{BASE}/auth/login', json=creds)
    if r.status_code != 200:
        return None
    return r.json().get('access_token')

def H(token):
    return {'Authorization': f'Bearer {token}'}


# ─── E2E-01: Flujo completo de registro y login de estudiante ─────────────────
class TestE2ERegistroEstudiante:
    """
    Flujo: Registro → Login → Verificación de token → Acceso al dashboard
    """
    email = f'e2e_student_{int(time.time())}@test.com'
    password = 'E2eTest123*'

    def test_01_registro(self):
        r = requests.post(f'{BASE}/auth/registro', json={
            'email': self.email,
            'password': self.password,
            'nombres': 'E2E',
            'apellidos': 'Estudiante',
        })
        assert r.status_code == 201, f'Fallo registro: {r.text}'
        d = r.json()
        assert d['usuario']['rol']['nombre'] == 'estudiante'
        TestE2ERegistroEstudiante.uid = d['usuario']['id']

    def test_02_login_con_nuevas_credenciales(self):
        r = requests.post(f'{BASE}/auth/login', json={
            'email': self.email, 'password': self.password
        })
        assert r.status_code == 200
        TestE2ERegistroEstudiante.token = r.json()['access_token']

    def test_03_token_es_verificable(self):
        r = requests.get(f'{BASE}/auth/verify', headers=H(self.token))
        assert r.status_code == 200

    def test_04_puede_acceder_a_sus_datos(self):
        r = requests.get(f'{BASE}/demografico/datos', headers=H(self.token))
        assert r.status_code == 200

    def test_05_no_puede_listar_todos_los_usuarios(self):
        r = requests.get(f'{BASE}/usuarios/', headers=H(self.token))
        assert r.status_code == 403

    def test_06_puede_ver_configuraciones_disponibles(self):
        r = requests.get(f'{BASE}/aplicaciones/disponibles', headers=H(self.token))
        assert r.status_code == 200
        assert 'configuraciones' in r.json()

    def test_07_puede_ver_sus_aplicaciones(self):
        r = requests.get(f'{BASE}/aplicaciones/mis-aplicaciones', headers=H(self.token))
        assert r.status_code == 200


# ─── E2E-02: Flujo completo TI — crear usuario y verificar en lista ──────────
class TestE2EGestionUsuariosTI:
    """
    Flujo: Login TI → Crear usuario → Verificar en lista → Buscar por nombre → Desactivar
    """
    email_nuevo = f'e2e_gestion_{int(time.time())}@test.com'

    def test_01_login_ti(self):
        TestE2EGestionUsuariosTI.token = get_token(ADMIN_TI)
        assert self.token is not None

    def test_02_crear_usuario(self):
        r = requests.post(f'{BASE}/usuarios/', headers=H(self.token), json={
            'email': self.email_nuevo,
            'password': 'GestionE2E1*',
            'nombres': 'Gestion',
            'apellidos': 'E2E',
            'rol': 'estudiante',
        })
        assert r.status_code == 201
        TestE2EGestionUsuariosTI.uid = r.json()['usuario']['id']

    def test_03_usuario_aparece_en_lista(self):
        r = requests.get(f'{BASE}/usuarios/', headers=H(self.token),
                         params={'buscar': 'Gestion'})
        assert r.status_code == 200
        emails = [u['email'] for u in r.json().get('usuarios', [])]
        assert self.email_nuevo in emails

    def test_04_obtener_usuario_por_id(self):
        r = requests.get(f'{BASE}/usuarios/{self.uid}', headers=H(self.token))
        assert r.status_code == 200
        u = r.json().get('usuario', {})
        assert u['id'] == self.uid
        assert 'created_at' in u

    def test_05_editar_usuario(self):
        r = requests.put(f'{BASE}/usuarios/{self.uid}', headers=H(self.token), json={
            'nombres': 'GestionEditado',
        })
        assert r.status_code == 200

    def test_06_desactivar_usuario(self):
        r = requests.put(f'{BASE}/usuarios/{self.uid}', headers=H(self.token), json={
            'activo': False,
        })
        assert r.status_code == 200
        assert r.json().get('usuario', {}).get('activo') is False

    def test_07_usuario_inactivo_no_puede_login(self):
        r = requests.post(f'{BASE}/auth/login', json={
            'email': self.email_nuevo, 'password': 'GestionE2E1*'
        })
        assert r.status_code in (401, 403)

    def test_08_reactivar_usuario(self):
        r = requests.put(f'{BASE}/usuarios/{self.uid}', headers=H(self.token), json={
            'activo': True,
        })
        assert r.status_code == 200
        assert r.json().get('usuario', {}).get('activo') is True


# ─── E2E-03: Flujo de fórmula de cálculo ─────────────────────────────────────
class TestE2EFormulasCalculo:
    """
    Flujo: Login TI → Crear fórmula JSON → Crear fórmula Código → Activar → Verificar activa
    """
    def test_01_login(self):
        TestE2EFormulasCalculo.token = get_token(ADMIN_TI)
        assert self.token is not None

    def test_02_crear_formula_formato_json(self):
        r = requests.post(f'{BASE}/demografico/formulas', headers=H(self.token), json={
            'nombre': f'Formula JSON E2E {int(time.time())}',
            'descripcion': 'Prueba E2E formato JSON',
            'tipo': 'holland_riasec',
            'parametros': {
                '_formato': 'json',
                'metodo': 'suma_binaria',
                'valor_positivo': 1,
                'valor_negativo': 0,
                'umbral_afinidad': 0.6,
            },
        })
        assert r.status_code == 201
        TestE2EFormulasCalculo.fid_json = r.json()['formula']['id']

    def test_03_crear_formula_formato_codigo(self):
        r = requests.post(f'{BASE}/demografico/formulas', headers=H(self.token), json={
            'nombre': f'Formula Código E2E {int(time.time())}',
            'descripcion': 'Prueba E2E formato código',
            'tipo': 'holland_riasec',
            'parametros': {
                '_formato': 'codigo',
                '_codigo': 'score = sum(1 for r in respuestas if r == 1) / len(respuestas)',
            },
        })
        assert r.status_code == 201
        TestE2EFormulasCalculo.fid_codigo = r.json()['formula']['id']

    def test_04_crear_formula_formato_csv(self):
        r = requests.post(f'{BASE}/demografico/formulas', headers=H(self.token), json={
            'nombre': f'Formula CSV E2E {int(time.time())}',
            'descripcion': 'Prueba E2E formato CSV',
            'tipo': 'holland_riasec',
            'parametros': {
                '_formato': 'csv',
                '_csv': 'area,metodo,umbral,peso\nRealista,suma_binaria,0.6,1.0',
                '_filas': [{'area': 'Realista', 'metodo': 'suma_binaria', 'umbral': '0.6', 'peso': '1.0'}],
            },
        })
        assert r.status_code == 201

    def test_05_activar_formula(self):
        r = requests.put(f'{BASE}/demografico/formulas/{self.fid_json}',
                         headers=H(self.token), json={'activa': True})
        assert r.status_code == 200

    def test_06_formula_aparece_en_lista(self):
        r = requests.get(f'{BASE}/demografico/formulas', headers=H(self.token))
        assert r.status_code == 200
        ids = [f['id'] for f in r.json().get('formulas', [])]
        assert self.fid_json in ids


# ─── E2E-04: Flujo de auditoría ───────────────────────────────────────────────
class TestE2EAuditoria:
    """
    Flujo: Login → Hacer acción registrable → Verificar que el log aparece
    """
    def test_01_login_genera_log(self):
        token = get_token(ADMIN_TI)
        assert token is not None
        TestE2EAuditoria.token = token

    def test_02_logs_contienen_entrada_de_login(self):
        r = requests.get(f'{BASE}/auditoria/logs', headers=H(self.token),
                         params={'modulo': 'auth', 'accion': 'LOGIN'})
        assert r.status_code == 200
        logs = r.json().get('logs', [])
        assert len(logs) > 0

    def test_03_filtro_por_accion_funciona(self):
        r = requests.get(f'{BASE}/auditoria/logs', headers=H(self.token),
                         params={'accion': 'LOGIN'})
        assert r.status_code == 200
        # El filtro puede retornar coincidencias parciales (LOGIN, LOGIN_FALLIDO, etc.)
        for log in r.json().get('logs', []):
            assert 'LOGIN' in log.get('accion', '')

    def test_04_crear_politica_retencion(self):
        r = requests.post(f'{BASE}/auditoria/politicas', headers=H(self.token), json={
            'nombre': f'Politica E2E {int(time.time())}',
            'descripcion': 'Retención prueba',
            'tiempo_retencion_dias': 365,
            'tabla_afectada': 'auditoria',
        })
        assert r.status_code == 201


# ─── E2E-05: Frontend — páginas cargan sin error 500 ─────────────────────────
class TestE2EFrontend:
    """Verifica que las páginas principales del frontend devuelven HTTP 200 o redirección."""

    def _session_con_login(self):
        s = requests.Session()
        s.post(f'{BASE_FRONT}/auth/login', data={
            'email': ADMIN_TI['email'],
            'password': ADMIN_TI['password'],
        }, allow_redirects=True)
        return s

    def test_landing_accesible(self):
        r = requests.get(f'{BASE_FRONT}/')
        assert r.status_code in (200, 302)

    def test_login_page_accesible(self):
        r = requests.get(f'{BASE_FRONT}/auth/login')
        assert r.status_code == 200

    def test_dashboard_redirige_sin_session(self):
        r = requests.get(f'{BASE_FRONT}/admin/dashboard', allow_redirects=False)
        assert r.status_code in (302, 303)

    def test_dashboard_carga_con_login(self):
        s = self._session_con_login()
        r = s.get(f'{BASE_FRONT}/admin/dashboard', allow_redirects=True)
        assert r.status_code == 200
        assert 'Dashboard' in r.text or 'dashboard' in r.url

    def test_usuarios_carga_con_login(self):
        s = self._session_con_login()
        r = s.get(f'{BASE_FRONT}/admin/usuarios', allow_redirects=True)
        assert r.status_code == 200
        assert 'Usuario' in r.text

    def test_formulas_carga_con_login(self):
        s = self._session_con_login()
        r = s.get(f'{BASE_FRONT}/admin/formulas-calculo', allow_redirects=True)
        assert r.status_code == 200
        assert 'F' in r.text  # página cargó contenido

    def test_auditoria_carga_con_login(self):
        s = self._session_con_login()
        r = s.get(f'{BASE_FRONT}/admin/auditoria', allow_redirects=True)
        assert r.status_code == 200

    def test_instrumento_carga_con_login(self):
        s = self._session_con_login()
        r = s.get(f'{BASE_FRONT}/admin/instrumento', allow_redirects=True)
        assert r.status_code == 200

    def test_exportar_carga_con_login(self):
        s = self._session_con_login()
        r = s.get(f'{BASE_FRONT}/admin/exportar', allow_redirects=True)
        assert r.status_code == 200
