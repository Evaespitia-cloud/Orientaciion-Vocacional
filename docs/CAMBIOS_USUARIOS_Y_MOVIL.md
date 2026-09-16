# Cambios: gestión de usuarios, registro y vista móvil

## 1. Admin: editar la contraseña de usuarios suscritos

**Backend** — `backend/app/controllers/usuario_controller.py`, `PUT /usuarios/<id>`

- Acepta un campo `password`. Si viene diligenciado, se valida con la misma
  política del registro (`AuthService.validar_password`) y se guarda hasheado con bcrypt.
- Solo el rol **TI** puede restablecer contraseñas (igual que con el cambio de rol).
  Bienestar sigue pudiendo editar datos, pero no contraseñas ni roles.
- La contraseña **nunca** se escribe en la auditoría: se registra un evento
  `RESTABLECER_PASSWORD` con el correo afectado y nada más.
- Se agregaron validaciones que antes faltaban: formato y unicidad de correo,
  unicidad de documento, y `rollback` + error 500 controlado si el commit falla
  (antes un correo repetido producía un IntegrityError sin manejar).
- `documento`, `telefono` y `cohorte` vacíos se guardan como `NULL`.

**Frontend** — `frontend/app/routes/admin_routes.py`, `frontend/app/templates/admin/usuarios.html`

- En la tabla, cada fila tiene ahora dos botones: **Editar** y **Contraseña**
  (este último abre el modal directo en la sección de contraseña).
- El modal de edición trae un bloque "Contraseña" plegado. Si se deja vacío,
  la contraseña no se toca.
- Campos de contraseña nueva + confirmación, cada uno con botón de ojo para
  mostrar/ocultar, y lista de requisitos que se marca en verde/rojo mientras se escribe.
- La validación corre en el navegador antes de enviar, así no se pierde el viaje al servidor.

## 2. Admin: crear usuarios con todos los campos

`frontend/app/templates/admin/usuarios.html` + `admin_routes.crear_usuario`

El modal "Nuevo Usuario" pasó de 5 campos a los mismos del registro público:

nombres, apellidos, tipo de documento, número de documento, correo, teléfono,
grado, cohorte, contraseña, confirmar contraseña, rol y estado.

- La contraseña tiene mostrar/ocultar y el mismo checklist de requisitos.
- Se exige confirmación de contraseña antes de enviar.

## 3. Revisión de perfiles / roles

Ajustes aplicados:

- Nuevo decorador `solo_ti` en `frontend/app/routes/admin_routes.py`. Se aplica a
  crear usuario, editar usuario y activar/desactivar. Antes esas rutas estaban
  abiertas a bienestar y directivo desde el frontend; el backend las rechazaba
  con 403, así que el usuario veía un error en lugar de un mensaje claro.
- `PUT /usuarios/<id>` ahora resuelve el rol del solicitante una sola vez y lo usa
  tanto para el cambio de rol como para el cambio de contraseña.

Matriz de permisos vigente sobre usuarios:

| Acción                  | estudiante | bienestar | directivo | investigador | ti |
|-------------------------|:---------:|:---------:|:---------:|:------------:|:--:|
| Ver listado de usuarios | –         | sí        | sí        | –            | sí |
| Crear usuario           | –         | –         | –         | –            | sí |
| Editar datos básicos    | –         | sí        | –         | –            | sí |
| Cambiar rol             | –         | –         | –         | –            | sí |
| Restablecer contraseña  | –         | –         | –         | –            | sí |
| Activar / desactivar    | –         | –         | –         | –            | sí |

Dos observaciones que quedan pendientes de decisión (no se tocaron):

1. `GET /usuarios/` permite a **bienestar** y **directivo** ver el listado completo,
   aunque el menú solo muestra "Usuarios" al rol TI. Entrando por URL directa sí
   pueden verlo. Si no debe ser así, hay que quitarlos de `roles_requeridos` en
   `listar_usuarios` y agregar `solo_ti` a la vista `admin.usuarios`.
2. Los modelos `Permiso` y `RolPermiso` existen y el decorador `permiso_requerido`
   está implementado, pero **ninguna ruta lo usa** y las tablas nunca se llenan
   (`init_deploy.py` solo siembra roles). Hoy todo el control de acceso es por rol.
   O se siembran los permisos y se usan, o conviene documentarlos como diseño futuro.

## 4. Registro: ya no se borra la información al fallar la contraseña

`frontend/app/routes/auth_routes.py` + `frontend/app/templates/auth/registro.html`

El problema: cuando el backend rechazaba el registro (contraseña sin carácter
especial, correo repetido, documento repetido…), la ruta hacía
`render_template('auth/registro.html')` sin devolver los datos, y el formulario
se volvía a pintar completamente vacío.

Ahora la ruta devuelve un diccionario `form` con lo que la persona ya había
escrito y la plantilla lo repuebla: nombres, apellidos, tipo y número de
documento, correo, teléfono, institución y grado (incluidos los `select`,
que quedan preseleccionados).

Los dos campos de contraseña sí se vacían a propósito — no se devuelven en el
HTML. El mensaje de error lo dice explícitamente: *"Vuelve a escribir la
contraseña; el resto de tus datos se conservó"*.

También se corrigió un bug relacionado en `AuthService.registrar_usuario`: un
documento vacío se guardaba como cadena `''` en vez de `NULL`, así que el
**segundo** registro sin documento chocaba contra la restricción `UNIQUE` y
devolvía un error 500 genérico.

## 5. Márgenes y centrado en móvil

`frontend/app/static/css/styles.css`

La causa principal del contenido "descentrado" era el desbordamiento horizontal:
cuando un elemento (tabla ancha, nombre largo en la barra, modal) supera el ancho
de la pantalla, el navegador crea scroll lateral y todo lo centrado con
`margin: 0 auto` se ve corrido hacia la izquierda con una franja en blanco a la derecha.

- `html` y `body` con `overflow-x: hidden` y `max-width: 100%`.
- `img, svg, canvas, video, iframe, pre` limitados a `max-width: 100%`.
- `.container` con `width: 100%` y márgenes automáticos explícitos.
- Barra de navegación: el nombre de usuario se trunca con puntos suspensivos
  (y se oculta bajo 480 px), y la marca no puede empujar el layout.
- Tablas: `min-width` solo dentro de `.table-container`, que ya tiene scroll propio,
  de modo que la tabla se desliza dentro de la tarjeta en vez de estirar la página.
- Modales: se les dio `padding` lateral para que la tarjeta no quede pegada a los
  bordes, y en pantallas pequeñas se reduce su relleno interno y su altura máxima.
- Páginas de login/registro: `align-items: flex-start` en móvil para que los
  formularios largos no queden cortados arriba, y la tarjeta usa el ancho disponible.
- Se desactivó el efecto `hover` de elevación de las tarjetas en pantallas táctiles,
  donde quedaba "pegado" tras cada toque.
- Se añadieron ajustes a 480 px: rejilla de estadísticas a una columna, tipografías
  de encabezado más pequeñas y botones a lo ancho.
