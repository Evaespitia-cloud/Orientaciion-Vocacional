"""Utilidad para hacer peticiones al backend API."""

import base64
import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from flask import current_app, session


def jwt_is_expired(token: str) -> bool:
    """Decodifica el payload JWT sin verificar firma y comprueba si ha expirado.

    Evita un round-trip HTTP al backend en cada petición protegida.
    """
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return True
        payload_b64 = parts[1]
        # Añadir padding necesario para base64
        payload_b64 += '=' * (-len(payload_b64) % 4)
        payload = json.loads(base64.b64decode(payload_b64))
        exp = payload.get('exp')
        if exp is None:
            return False  # Sin expiración definida
        return time.time() > exp
    except Exception:
        return True  # Si no se puede decodificar, tratar como expirado


def _build_http_session():
    """Crea una sesión HTTP con pool de conexiones persistentes."""
    s = requests.Session()
    adapter = HTTPAdapter(
        pool_connections=4,   # conexiones simultáneas al backend
        pool_maxsize=20,      # máximo de conexiones en el pool
    )
    s.mount('http://', adapter)
    s.mount('https://', adapter)
    return s


# Pool de conexiones compartido — reutiliza TCP entre requests (HTTP Keep-Alive)
_http = _build_http_session()


def api_request(method, endpoint, data=None, params=None):
    """Realizar una petición al backend API."""
    base_url = current_app.config['BACKEND_API_URL']
    url = f"{base_url}{endpoint}"
    headers = {'Content-Type': 'application/json'}

    token = session.get('access_token')
    if token:
        headers['Authorization'] = f'Bearer {token}'

    try:
        response = _http.request(
            method=method,
            url=url,
            json=data,
            params=params,
            headers=headers,
            timeout=10,
        )
        try:
            return response.json(), response.status_code
        except (ValueError, requests.exceptions.JSONDecodeError):
            return {'error': f'Respuesta no válida del servidor (HTTP {response.status_code})'}, response.status_code
    except requests.exceptions.ConnectionError:
        return {'error': 'No se puede conectar con el servidor. Verifique que el backend esté ejecutándose.'}, 503
    except Exception:
        return {'error': 'Error de conexión con el servicio.'}, 500


def api_requests_parallel(calls):
    """Ejecutar múltiples llamadas API en paralelo usando el pool de conexiones.

    calls: lista de tuplas (key, method, endpoint) o (key, method, endpoint, data, params)
    Retorna: dict {key: (data_dict, status_code)}
    """
    # Extraer contexto Flask ANTES de crear hilos (los hilos no tienen acceso a proxies locales)
    base_url = current_app.config['BACKEND_API_URL']
    token = session.get('access_token')

    def _fetch(call):
        key      = call[0]
        method   = call[1]
        endpoint = call[2]
        body     = call[3] if len(call) > 3 else None
        params   = call[4] if len(call) > 4 else None

        url = f"{base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        try:
            response = _http.request(
                method=method, url=url, json=body,
                params=params, headers=headers, timeout=10,
            )
            try:
                return key, (response.json(), response.status_code)
            except (ValueError, requests.exceptions.JSONDecodeError):
                return key, ({'error': f'Respuesta no válida (HTTP {response.status_code})'}, response.status_code)
        except requests.exceptions.ConnectionError:
            return key, ({'error': 'No se puede conectar con el servidor.'}, 503)
        except Exception:
            return key, ({'error': 'Error de conexión con el servicio.'}, 500)

    results = {}
    workers = min(len(calls), 8)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_fetch, call) for call in calls]
        for future in as_completed(futures):
            key, result = future.result()
            results[key] = result

    return results


def api_request_file(method, endpoint, data=None, params=None):
    """Realizar una petición al backend y devolver la respuesta binaria (para proxear archivos).

    Retorna un objeto requests.Response crudo para que el caller pueda
    leer .content, .headers['Content-Type'] y .headers['Content-Disposition'].
    Devuelve None en caso de error de conexión.
    """
    base_url = current_app.config['BACKEND_API_URL']
    url = f"{base_url}{endpoint}"
    headers = {}

    token = session.get('access_token')
    if token:
        headers['Authorization'] = f'Bearer {token}'

    try:
        response = _http.request(
            method=method,
            url=url,
            json=data,
            params=params,
            headers=headers,
            timeout=30,   # archivos pueden tardar más
            stream=True,
        )
        return response
    except Exception:
        return None
