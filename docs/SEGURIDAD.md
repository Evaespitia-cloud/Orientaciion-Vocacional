# Ciberseguridad aplicada

La seguridad fue organizada sin eliminar la lógica funcional del proyecto.

## Identidad y autenticación

- Las contraseñas se almacenan con bcrypt, nunca en texto plano.
- Nuevas contraseñas deben tener mínimo 10 caracteres e incluir mayúscula, minúscula, número y carácter especial.
- El endpoint de registro público fuerza el rol `estudiante`; no acepta elevación de privilegios desde el cliente.
- Los mensajes de login inválido no revelan si el correo existe.
- Los tokens JWT expiran y se aceptan únicamente desde el encabezado `Authorization`.

## Sesiones y navegador

- El frontend utiliza sesiones del lado del servidor con `Flask-Session`.
- Cookies `HttpOnly` y `SameSite=Lax`.
- En producción las cookies son `Secure`.
- Los formularios y acciones mutables del frontend están protegidos con token CSRF.

## Protección de endpoints

- RBAC para limitar funciones por rol.
- Validación del usuario propietario antes de entregar o modificar información privada.
- Las respuestas solo se aceptan para ítems activos y pertenecientes al instrumento de la aplicación.
- Login y registro poseen limitación básica de intentos.
- CORS no queda abierto globalmente; usa `ALLOWED_ORIGINS`.

## Cabeceras HTTP

Se configuran, entre otras:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy`
- `Permissions-Policy`
- `Content-Security-Policy` en frontend
- `Strict-Transport-Security` en producción

## Secretos y producción

Los `.env` reales, bases locales, dumps, sesiones y claves locales no forman parte de la entrega. En producción son obligatorias las variables sensibles y las claves deben tener al menos 32 caracteres.

## Auditoría y trazabilidad

El proyecto conserva su módulo de auditoría. Los ítems del banco se desactivan en lugar de borrarse para no romper resultados históricos.

## Recomendaciones para despliegue real

Para un despliegue institucional todavía deben hacerse controles de infraestructura: HTTPS en proxy/balanceador, PostgreSQL administrado, backups cifrados, rotación de secretos, monitoreo, gestión de vulnerabilidades y un almacén compartido como Redis para sesiones/rate limiting en despliegues multi-worker.
