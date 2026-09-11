"""Configuración segura del frontend — conexión con el backend API."""

import os
import secrets
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
_BASE_DIR = Path(__file__).resolve().parents[1]
_INSTANCE_DIR = _BASE_DIR / 'instance'
_INSTANCE_DIR.mkdir(parents=True, exist_ok=True)


def _local_secret() -> str:
    value = os.getenv('SECRET_KEY')
    if value:
        return value
    path = _INSTANCE_DIR / '.frontend_secret_key'
    if path.exists():
        return path.read_text(encoding='utf-8').strip()
    value = secrets.token_urlsafe(48)
    path.write_text(value, encoding='utf-8')
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return value


class Config:
    SECRET_KEY = _local_secret()
    BACKEND_API_URL = os.getenv('BACKEND_API_URL', 'http://localhost:5000/api')
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = str(_INSTANCE_DIR / 'sessions')
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 2 * 1024 * 1024))


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
}


def validate_production_environment(config_name: str) -> None:
    if config_name != 'production':
        return
    missing = [name for name in ('SECRET_KEY', 'BACKEND_API_URL') if not os.getenv(name)]
    if missing:
        raise RuntimeError('Configuración frontend de producción incompleta: ' + ', '.join(missing))
    if len(os.getenv('SECRET_KEY', '')) < 32:
        raise RuntimeError('SECRET_KEY del frontend debe tener al menos 32 caracteres en producción.')
