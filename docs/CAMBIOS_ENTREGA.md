# Cambios de esta entrega

## Qué se conserva

Se conservaron todos los archivos funcionales del backend, frontend y SQL del proyecto completo recibido. No se eliminó ningún controlador, servicio, modelo, ruta, plantilla o script SQL de la aplicación.

Los módulos funcionales permanecen: autenticación, usuarios y roles, consentimiento, datos demográficos, instrumentos, configuraciones, aplicación/autoguardado, procesamiento psicométrico, resultados, evolución, reportes PDF, estadísticas, consultas, exportación, ML/K-Means, PLN y auditoría.

## Banco de preguntas vigente

La única fuente oficial es `data/Items Full day.xlsx`.

- Intereses: 30 ítems.
- Competencias: 30 ítems.
- Total activo esperado: 60 ítems.

`importar_banco_cliente.py` valida las cantidades antes de sincronizar, desactiva ítems anteriores en lugar de borrarlos y verifica la postcondición 30 + 30.

El listado administrativo de ítems muestra por defecto solo los ítems activos. Los históricos pueden consultarse explícitamente con `incluir_inactivos=true` desde la API.

## Seguridad mejorada

- `.env`, dumps, BD locales y PDFs generados no se distribuyen dentro del ZIP.
- Secretos obligatorios en producción.
- Claves locales de desarrollo generadas automáticamente si no existen.
- Registro público limitado al rol estudiante.
- Contraseñas robustas y bcrypt.
- Eliminado el bypass de contraseña compartida de estudiantes.
- JWT únicamente por encabezado Authorization.
- Sesiones del frontend almacenadas del lado del servidor con Flask-Session.
- Protección CSRF para operaciones que modifican estado.
- Límite básico de intentos en login y registro.
- CORS restringido.
- Cabeceras de seguridad y HSTS en producción.
- Mayor control de acceso al consultar usuarios y modificar roles.
- Validación de que las respuestas correspondan a ítems activos del instrumento actual.
- Soft-delete de ítems para proteger trazabilidad y resultados históricos.

## Archivos no incluidos deliberadamente

Se excluyeron `.venv`, cachés de Python/pytest, el `.env` real, dumps de base de datos, una BD SQLite vacía y reportes PDF ya generados. Estos archivos son locales, generados o potencialmente sensibles y no hacen parte del código funcional de la aplicación.
