"""Limitador sencillo para endpoints sensibles.

Para despliegues con varios workers se recomienda sustituirlo por un almacén
compartido (Redis/Flask-Limiter en infraestructura).
"""
from collections import defaultdict, deque
from threading import Lock
from time import monotonic

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
