"""Servidores aislados para las pruebas de integración y e2e.

Al importarse levanta, una sola vez por corrida, un backend (puerto 5055) y un
frontend (puerto 5056) contra una base SQLite temporal con el esquema, el banco
de preguntas y tres usuarios de prueba. Así las pruebas nunca escriben en la
base de desarrollo. Todo se apaga y se borra al terminar.

Con PRUEBAS_API y PRUEBAS_FRONT definidas se usan esos servidores en su lugar.
"""

import atexit
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
RAIZ = BACKEND.parent
PUERTO_API, PUERTO_FRONT = 5055, 5056

ADMIN_TI = {'email': 'admin@pruebas.local', 'password': 'AdminPruebas1*'}
BIENESTAR = {'email': 'bienestar@pruebas.local', 'password': 'Bienestar1Prueba*'}
ESTUDIANTE = {'email': 'estudiante@pruebas.local', 'password': 'Estudiante1Prueba*'}

_SEMBRAR = f"""
from app import create_app
from app.extensions import db
from app.services.auth_service import AuthService
app = create_app('development')
with app.app_context():
    for email, clave, rol, nombre in [
        ({BIENESTAR['email']!r}, {BIENESTAR['password']!r}, 'bienestar', 'Bienestar'),
        ({ESTUDIANTE['email']!r}, {ESTUDIANTE['password']!r}, 'estudiante', 'Estudiante'),
    ]:
        AuthService.registrar_usuario({{'email': email, 'password': clave, 'rol': rol,
                                        'nombres': nombre, 'apellidos': 'Pruebas'}})
"""


def _esperar(url, segundos=60):
    limite = time.time() + segundos
    while time.time() < limite:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except urllib.error.HTTPError:
            return True  # respondió, aunque sea con error
        except Exception:
            time.sleep(0.4)
    return False


def _levantar():
    temporal = tempfile.mkdtemp(prefix='ov_pruebas_')
    base = Path(temporal, 'pruebas.db').as_posix()
    env = dict(os.environ, FLASK_ENV='development', DATABASE_URL=f'sqlite:///{base}',
               ADMIN_EMAIL=ADMIN_TI['email'], ADMIN_PASSWORD=ADMIN_TI['password'],
               ALLOWED_ORIGINS=f'http://127.0.0.1:{PUERTO_FRONT}', PYTHONIOENCODING='utf-8',
               GEOCODIFICAR_OSM='0')
    salida = open(Path(temporal, 'servidores.log'), 'w', encoding='utf-8')
    py = sys.executable
    subprocess.run([py, 'init_deploy.py'], cwd=BACKEND, env=env, check=True, stdout=salida, stderr=salida)
    subprocess.run([py, str(RAIZ / 'scripts' / 'maintenance' / 'importar_banco_cliente.py')],
                   cwd=RAIZ, env=env, check=True, stdout=salida, stderr=salida)
    subprocess.run([py, '-c', _SEMBRAR], cwd=BACKEND, env=env, check=True, stdout=salida, stderr=salida)

    arranque = ("from app import create_app; create_app('development').run("
                "host='127.0.0.1', port={puerto}, debug=False, use_reloader=False)")
    procesos = [subprocess.Popen([py, '-c', arranque.format(puerto=PUERTO_API)], cwd=BACKEND, env=env,
                                 stdout=salida, stderr=salida)]
    env_front = dict(env, BACKEND_API_URL=f'http://127.0.0.1:{PUERTO_API}/api')
    procesos.append(subprocess.Popen([py, '-c', arranque.format(puerto=PUERTO_FRONT)], cwd=RAIZ / 'frontend',
                                     env=env_front, stdout=salida, stderr=salida))

    def apagar():
        for p in procesos:
            p.terminate()
        for p in procesos:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
        salida.close()
        shutil.rmtree(temporal, ignore_errors=True)

    atexit.register(apagar)
    if not (_esperar(f'http://127.0.0.1:{PUERTO_API}/api/health') and _esperar(f'http://127.0.0.1:{PUERTO_FRONT}/')):
        raise RuntimeError(f'No arrancaron los servidores de prueba; ver {salida.name}')
    return f'http://127.0.0.1:{PUERTO_API}/api', f'http://127.0.0.1:{PUERTO_FRONT}'


_tokens = {}


def token(creds):
    """Token JWT de unas credenciales, pedido una sola vez.

    El backend limita los inicios de sesión por correo (10 cada 5 minutos);
    sin esta caché las pruebas se bloquean a sí mismas con 429.
    """
    clave = (creds['email'], creds['password'])
    if clave not in _tokens:
        import json
        pedido = urllib.request.Request(f'{API}/auth/login', data=json.dumps(creds).encode(),
                                        headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(pedido, timeout=10) as r:
                _tokens[clave] = json.loads(r.read().decode()).get('access_token')
        except urllib.error.HTTPError:
            return None
    return _tokens[clave]


if os.getenv('PRUEBAS_API') and os.getenv('PRUEBAS_FRONT'):
    API, FRONT = os.environ['PRUEBAS_API'], os.environ['PRUEBAS_FRONT']
else:
    API, FRONT = _levantar()
