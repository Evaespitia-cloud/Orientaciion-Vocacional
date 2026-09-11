# Arquitectura del proyecto

## 1. Capa de presentación

`frontend/` contiene la interfaz web. Sus rutas consumen la API del backend y mantienen la sesión del navegador en el servidor. Las plantillas están separadas por autenticación, estudiante y administración.

## 2. API y controladores

`backend/app/controllers/` contiene los endpoints por dominio: autenticación, usuarios, consentimiento, configuración, instrumentos, aplicaciones, procesamiento, reportes, estadísticas, consultas, exportaciones, auditoría, demografía y ML.

## 3. Servicios

`backend/app/services/` concentra reglas que no deben vivir dentro de las rutas: autenticación, procesamiento psicométrico, reportes, estadística, clustering y PLN.

## 4. Persistencia

`backend/app/models/` contiene los modelos SQLAlchemy. `backend/sql/` conserva inicialización, migraciones e índices.

## 5. Banco oficial de preguntas

`data/Items Full day.xlsx` es la fuente oficial. El importador valida como precondición exactamente 30 ítems de Intereses y 30 de Competencias y, después de sincronizar, vuelve a comprobar que existan exactamente 30 activos de cada prueba.

## 6. Herramientas auxiliares

Los scripts que antes estaban mezclados en la raíz se agrupan por propósito dentro de `scripts/`. Deben ejecutarse desde la raíz usando `python -m`, por ejemplo:

```bash
python -m scripts.maintenance.importar_banco_cliente --dry-run
python -m scripts.database.backup_database
```

Esta separación evita mezclar utilidades de mantenimiento con el código que atiende usuarios.
