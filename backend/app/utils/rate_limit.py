"""Limitador sencillo para endpoints sensibles.

Para despliegues con varios workers se recomienda sustituirlo por un almacén
compartido (Redis/Flask-Limiter en infraestructura).
"""
from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from flask import request

# El frontend le habla al backend desde la misma máquina y le pasa la IP del visitante
# en este encabezado. Solo se le cree cuando la petición viene de ahí.
CABECERA_IP = 'X-Cliente-IP'
PROXIES_LOCALES = ('127.0.0.1', '::1')

_attempts = defaultdict(deque)
_lock = Lock()


def allow_request(key: str, limit: int, window_seconds: int) -> bool:
    now = monotonic()
    cutoff = now - window_seconds
    with _lock:
        bucket = _attempts[key]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True


def ip_cliente():
    """IP del visitante. Sin esto, detrás del frontend todos compartirían 127.0.0.1
    y un límite "por IP" sería en realidad un límite para todo el sitio."""
    if request.remote_addr in PROXIES_LOCALES:
        reenviada = (request.headers.get(CABECERA_IP) or '').strip()
        if reenviada:
            return reenviada[:64]
    return request.remote_addr or 'desconocida'
