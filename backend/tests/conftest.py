"""Rutas para que las pruebas corran igual desde la raíz del repo o desde backend/."""

import os
import sys

# Antes de importar cualquier parte de la app: la configuración lee DATABASE_URL al
# cargarse y, sin esto, las pruebas en proceso usarían la base de desarrollo del .env.
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ.setdefault('FLASK_ENV', 'development')

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
for ruta in (RAIZ, os.path.join(RAIZ, 'backend')):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)
