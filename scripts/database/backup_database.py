"""Genera un respaldo PostgreSQL sin exponer credenciales.

Usa DATABASE_URL desde backend/.env o desde el entorno actual.
Ejemplo:
    py backup_database.py
    py backup_database.py --output-dir backups --format custom
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('backups'))
    parser.add_argument('--format', choices=('plain', 'custom'), default='custom')
    return parser.parse_args()


def connection_from_environment() -> tuple[list[str], dict[str, str]]:
    load_dotenv(Path(__file__).parent / 'backend' / '.env')
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise RuntimeError('DATABASE_URL no está definido.')

    parsed = urlparse(database_url)
    if parsed.scheme not in ('postgresql', 'postgres'):
        raise RuntimeError('El respaldo requiere una conexión PostgreSQL.')
    if not parsed.hostname or not parsed.path.strip('/'):
        raise RuntimeError('DATABASE_URL no contiene host y base de datos válidos.')

    command = [
        'pg_dump',
        '--host', parsed.hostname,
        '--port', str(parsed.port or 5432),
        '--username', unquote(parsed.username or ''),
        '--dbname', parsed.path.lstrip('/'),
        '--no-owner',
        '--no-privileges',
    ]
    environment = os.environ.copy()
    if parsed.password is not None:
        environment['PGPASSWORD'] = unquote(parsed.password)
    return command, environment


def locate_pg_dump() -> str | None:
    """Encuentra pg_dump en PATH o en instalaciones estándar de Windows."""
    candidates = [shutil.which('pg_dump')]
    program_files = os.environ.get('ProgramFiles', r'C:\Program Files')
    candidates.extend(sorted(Path(program_files).glob('PostgreSQL/*/bin/pg_dump.exe'), reverse=True))
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    return None


def main() -> int:
    args = parse_args()
    pg_dump = locate_pg_dump()
    if not pg_dump:
        raise RuntimeError('No se encontró pg_dump. Instala PostgreSQL o agrega su carpeta bin al PATH.')

    command, environment = connection_from_environment()
    command[0] = pg_dump
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    extension = 'sql' if args.format == 'plain' else 'dump'
    output = args.output_dir / f'orientacion_{timestamp}.{extension}'

    command.insert(1, '--format')
    command.insert(2, 'p' if args.format == 'plain' else 'c')
    command.extend(['--file', str(output)])
    completed = subprocess.run(command, env=environment, capture_output=True, text=True)
    if completed.returncode != 0:
        if output.exists():
            output.unlink()
        message = completed.stderr.strip() or 'pg_dump terminó con error.'
        raise RuntimeError(message)

    print(f'Respaldo creado: {output}')
    print(f'Tamaño: {output.stat().st_size} bytes')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f'ERROR: {error}')
        raise SystemExit(1)
