"""Configuración segura del backend API."""

import os
import secrets
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

_BASE_DIR = Path(__file__).resolve().parents[1]
_INSTANCE_DIR = _BASE_DIR / "instance"
_INSTANCE_DIR.mkdir(parents=True, exist_ok=True)


def _local_secret(name: str) -> str:
    """Obtiene/crea una clave local persistente sin dejar secretos en el repositorio."""
    env_value = os.getenv(name)
    if env_value:
        return env_value
    path = _INSTANCE_DIR / f".{name.lower()}"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    value = secrets.token_urlsafe(48)
    path.write_text(value, encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return value


def _url_base_datos() -> str:
    """Normaliza la cadena de conexión y fija el driver de PostgreSQL.

    El proveedor entrega la URL como "postgresql://" (algunos, como Heroku, aún
    usan "postgres://"). Qué librería se usa para conectarse depende entonces del
    valor por defecto de SQLAlchemy, que cambió de psycopg2 a psycopg (v3) en la
    versión 2.1 y tumbó el despliegue. Al escribir "+psycopg2" el driver queda
    declarado y no depende de la versión que se instale.
    """
    url = os.getenv('DATABASE_URL', 'sqlite:///orientacion.db')
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]
    if url.startswith('postgresql://'):
        url = 'postgresql+psycopg2://' + url[len('postgresql://'):]
    return url


class Config:
    """Configuración base del backend."""
    SECRET_KEY = _local_secret('SECRET_KEY')
    JWT_SECRET_KEY = _local_secret('JWT_SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = _url_base_datos()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # El frontend envía JWT en Authorization: Bearer; no se aceptan JWT desde cookies.
    JWT_TOKEN_LOCATION = ['headers']
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)

    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 2 * 1024 * 1024))
    JSON_SORT_KEYS = False


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
}


def validate_production_environment(config_name: str) -> None:
    """Evita arrancar producción con secretos o BD implícitos."""
    if config_name != 'production':
        return
    missing = [name for name in ('SECRET_KEY', 'JWT_SECRET_KEY', 'DATABASE_URL') if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            'Configuración de producción incompleta. Faltan variables: ' + ', '.join(missing)
        )
    if len(os.getenv('SECRET_KEY', '')) < 32 or len(os.getenv('JWT_SECRET_KEY', '')) < 32:
        raise RuntimeError('SECRET_KEY y JWT_SECRET_KEY deben tener al menos 32 caracteres en producción.')
