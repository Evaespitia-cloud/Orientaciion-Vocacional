# Scripts auxiliares

Ejecuta estas herramientas **desde la raíz del proyecto** con `python -m`.

- `database/`: respaldo de base de datos.
- `diagnostics/`: inspecciones, verificaciones y pruebas manuales.
- `maintenance/`: sincronización del banco y correcciones controladas.
- `migrations/`: migraciones auxiliares.
- `seeds/`: datos de demostración/desarrollo. No ejecutar en producción sin revisión previa.

Ejemplo:

```bash
python -m scripts.maintenance.importar_banco_cliente --dry-run
```
