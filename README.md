# Orientación Vocacional — arquitectura organizada y seguridad reforzada

Esta entrega parte del **proyecto completo** y conserva su lógica funcional: backend, frontend, pruebas, resultados, reportes, exportaciones, estadística, ML/PLN, auditoría y administración. La reorganización se hizo para separar claramente aplicación, datos, documentación, referencias y scripts auxiliares.

## Banco oficial

La fuente oficial está en:

`data/Items Full day.xlsx`

El sistema trabaja con:

- 30 preguntas de **Intereses**.
- 30 preguntas de **Competencias**.
- 60 códigos únicos en total.

El importador oficial está en:

`python -m scripts.maintenance.importar_banco_cliente --dry-run`

Para aplicar la sincronización a la base de datos:

`python -m scripts.maintenance.importar_banco_cliente`

Los ítems antiguos se desactivan para preservar historial; no se eliminan físicamente.

## Arquitectura

```text
OrientacionVocacional-arquitectura-segura/
├── backend/                 API y lógica de negocio
│   ├── app/
│   │   ├── controllers/     Endpoints REST
│   │   ├── models/          Modelos SQLAlchemy
│   │   ├── schemas/         Esquemas
│   │   ├── services/        Reglas de negocio, psicometría, ML/PLN, reportes
│   │   └── utils/           RBAC, auditoría, rate limiting
│   ├── sql/                 Scripts y migraciones SQL
│   ├── tests/               Pruebas automatizadas
│   ├── instance/            Archivos locales no versionados
│   └── run.py
├── frontend/                Aplicación web Flask
│   ├── app/
│   │   ├── routes/          Rutas de interfaz
│   │   ├── templates/       Vistas HTML
│   │   └── static/          CSS e imágenes
│   ├── instance/            Sesiones/secretos locales no versionados
│   └── run.py
├── data/                    Banco oficial de preguntas
├── references/              PDFs de referencia del instrumento
├── scripts/
│   ├── database/            Copias de seguridad
│   ├── diagnostics/         Inspección y diagnóstico
│   ├── maintenance/         Correcciones y sincronización del banco
│   ├── migrations/          Utilidades de migración
│   └── seeds/               Datos de prueba/desarrollo
└── docs/                    Arquitectura, seguridad y documentación
```

## Seguridad incorporada

- Contraseñas con bcrypt.
- Política mínima de contraseña.
- El registro público solo puede crear estudiantes.
- JWT enviado únicamente mediante `Authorization: Bearer`.
- Sesiones del frontend del lado del servidor.
- CSRF para operaciones que modifican datos desde el frontend.
- Rate limiting básico para login y registro.
- Validación de propiedad/pertenencia de aplicaciones, respuestas e ítems.
- RBAC para módulos administrativos.
- Cabeceras HTTP de seguridad.
- CORS limitado a orígenes autorizados.
- Secretos fuera del repositorio.
- Configuración de producción que exige secretos y `DATABASE_URL` explícitos.
- Soft delete de preguntas para conservar trazabilidad.
- Auditoría de acciones relevantes.

Consulta `docs/SEGURIDAD.md` y `docs/ARQUITECTURA.md`.

## Ejecución local

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python run.py
```

### 2. Frontend

En otra terminal:

```bash
cd frontend
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python run.py
```

Backend por defecto: `http://localhost:5000`  
Frontend por defecto: `http://localhost:5001`

## Producción

No uses las claves de ejemplo. En producción configura `FLASK_ENV=production`, HTTPS, PostgreSQL, secretos independientes y fuertes, backups cifrados y un almacén compartido para rate limiting/sesiones si se despliega con varios workers.
