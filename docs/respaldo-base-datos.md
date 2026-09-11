# Respaldo de la base de datos

El respaldo PostgreSQL se genera con `backup_database.py` usando `DATABASE_URL`
de `backend/.env`. Las credenciales no se imprimen ni se guardan en el nombre
del archivo. En Windows, el script busca `pg_dump` en el PATH y en las rutas
estándar de instalación de PostgreSQL.

```powershell
.\.venv\Scripts\python.exe backup_database.py
```

El archivo se crea en `backups/` con fecha y hora. Para obtener un SQL legible:

```powershell
.\.venv\Scripts\python.exe backup_database.py --format plain
```

Para restaurar un respaldo custom en una base vacía:

```powershell
pg_restore --clean --if-exists --no-owner --dbname orientacion backups\archivo.dump
```

Antes de restaurar en producción, detener temporalmente la aplicación y verificar
que el respaldo corresponda al entorno correcto. Mantener la carpeta `backups/`
fuera de repositorios públicos y aplicar una política de retención.
