# Publicar en Render

Este paquete está preparado para obtener **un único enlace público**. El servicio web ejecuta el frontend y la API backend en el mismo contenedor; PostgreSQL persiste usuarios, respuestas y resultados.

## Subida
1. Crea un repositorio privado en GitHub y sube el contenido de esta carpeta (no el ZIP dentro del repositorio).
2. En Render, usa **New > Blueprint** y conecta ese repositorio.
3. Render detectará `render.yaml` y creará el servicio web + PostgreSQL.
4. Al crear el Blueprint, Render pedirá `ADMIN_EMAIL` y `ADMIN_PASSWORD`. Usa una contraseña de al menos 10 caracteres con mayúscula, minúscula, número y símbolo.
5. Finaliza el despliegue. Render entregará una URL `https://...onrender.com`.

## Qué hace automáticamente
- Crea las tablas si no existen.
- Crea los roles requeridos.
- Crea los dos instrumentos y las seis escalas RIASEC de cada uno.
- Importa el banco oficial: **30 Intereses + 30 Competencias**.
- Arranca backend en la red interna del contenedor y frontend en el puerto público asignado por Render.

## Seguridad
Los secretos no están dentro del repositorio. Render genera `SECRET_KEY` y `JWT_SECRET_KEY`. La base PostgreSQL no permite acceso público por IP (`ipAllowList: []`).

## Local
El despliegue no impide seguir ejecutando backend y frontend localmente como antes.
