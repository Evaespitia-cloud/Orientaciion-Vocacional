# DOCUMENTO HISTÓRICO — BANCO SUSTITUIDO

> La versión vigente usa únicamente `data/Items Full day.xlsx`: 30 Intereses + 30 Competencias. Las cantidades 60/64 o 30/18 descritas abajo son históricas y no corresponden al banco actual.

# Actualizaciones de la Plataforma — Versión de Simulación

**Fecha:** 30 de agosto de 2026
**Motivo:** Adaptar el software a los requisitos entregados por el cliente en los
documentos *"Lineamientos para la versión de simulación"* y *"Formato juicio
situacional — Escala de competencias/habilidades vocacionales"*.

Este documento compara el estado del sistema **antes** y **después** de la
actualización, separando los cambios **visuales** (lo que ve el estudiante/administrador)
de los cambios **técnicos** (arquitectura, datos y motor de cálculo).

---

## 1. Resumen ejecutivo

| Aspecto | Antes | Después |
|---|---|---|
| Escala de Intereses | 30 ítems Sí/No sobre una sola afirmación | **60 fichas de comparación binaria** entregadas por el cliente, con dos alternativas RIASEC y puntuación 1/0 |
| Escala de Competencias | 18 ítems de opción múltiple (3 por campo), respuesta correcta/incorrecta | **64 ítems de juicio situacional** entregados por el cliente, con 4 opciones graduadas 1-4 puntos |
| Balance por campo RIASEC | Desigual (algunos campos con más ítems que otros) | Se conservan las cantidades del banco del cliente; la normalización usa el máximo real de cada campo |
| Motor de puntuación | Suma binaria simple (1/0) | Puntajes graduados (1-4) y contribución a dos campos por ítem |
| Perfil integrado | Promedio simple entre intereses y competencias | Cruce del **ranking de intereses** (1º, 2º, 3º) con el **% de competencias** por campo |
| Exportación de datos | Solo CSV (resultados y estadísticas agregadas) | CSV + nuevo **Excel completo** con 6 hojas (identificación, aplicación, respuestas, intereses, competencias, perfil integrado) |
| Seguridad de la clave de calificación | Se enviaba al navegador junto con el ítem | Oculta para el estudiante; solo visible para roles administrativos |
| Registro del estudiante | Sin campo de grupo/curso | Se agregó el campo demográfico "Grupo o Curso" |

---

## 2. Cambios visuales (interfaz del estudiante)

### 2.1 Prueba de Intereses

**Antes:** cada pregunta mostraba una afirmación única con dos botones grandes
"Sí" / "No" (por ejemplo: *"¿Te gusta trabajar con herramientas, máquinas o
equipos?"*).

**Después:** cada pregunta presenta **dos tarjetas** (A y B) una junto a la otra,
cada una describiendo una actividad distinta asociada a un campo RIASEC
diferente, y el estudiante elige la que prefiere (por ejemplo: *A) Trabajar con
herramientas, máquinas o equipos* vs. *B) Resolver problemas complejos mediante
el análisis*). Esto refleja el formato de comparación forzada pedido en los
lineamientos, en vez de una simple afirmación aislada.

### 2.2 Prueba de Competencias

**Antes:** opción múltiple simple, 3 alternativas de texto corto, sin contexto
ni escenario, una sola opción "correcta".

**Después:** cada ítem incluye:
- Un **bloque de contexto/escenario** destacado (fondo gris claro, borde de
  color, texto en cursiva) que describe la situación.
- El enunciado de la acción a evaluar.
- **4 opciones (A-D)** graduadas en calidad de respuesta, sin mostrar nunca el
  puntaje interno al estudiante.

### 2.3 Panel de administración / exportación

**Antes:** la pantalla de exportación solo ofrecía descargar CSV (resultados
anonimizados/identificados y estadísticas agregadas).

**Después:** se agregó una tercera tarjeta "Base Exportable Completa (Excel)"
que descarga un archivo `.xlsx` con la estructura mínima exigida por el
cliente (identificación, aplicación, respuestas por ítem, intereses,
competencias y perfil integrado).

---

## 3. Cambios técnicos (backend y datos)

### 3.1 Banco de ítems

| | Antes | Después |
|---|---|---|
| Tipo de ítem — Intereses | `eleccion_forzada` (Sí/No) | `comparacion_binaria` (elige A o B entre dos campos RIASEC) |
| Tipo de ítem — Competencias | `opcion_multiple` (3 opciones, 1 correcta) | `juicio_situacional` (4 opciones graduadas 1-4) |
| Cantidad de ítems | 30 (Intereses) + 18 (Competencias) = 48 | 60 (Intereses) + 64 (Competencias) = 124 |
| Estructura de `opciones` (JSON) | `{"positivo": "Sí", "negativo": "No"}` u `{"opciones": [{"texto", "valor": 0/1}]}` | Intereses: `{"opcion_a": {"campo","texto"}, "opcion_b": {"campo","texto"}}` · Competencias: `{"opciones": [{"letra","texto","puntaje": 1-4}]}` |
| Campo de contexto/escenario | No existía | Nueva columna `Item.contexto` |
| Código e identificador de versión del ítem | No existía | Nuevas columnas `Item.codigo` y `Item.version` |

Archivos modificados: [backend/app/models/instrumento.py](../backend/app/models/instrumento.py),
importador [importar_banco_cliente.py](../importar_banco_cliente.py),
migración histórica [migrate_simulacion_juicio_situacional.py](../migrate_simulacion_juicio_situacional.py),
restricción de base de datos [backend/sql/update_constraint.sql](../backend/sql/update_constraint.sql).

### 3.2 Motor de puntuación (`PsicometricoService`)

**Antes:** una única función (`_es_respuesta_positiva`) determinaba si una
respuesta era "positiva" (1 punto) o no, sumando puntos binarios por escala.

**Después:** el motor se rediseñó para soportar puntajes graduados y para que
un mismo ítem pueda aportar a **dos campos RIASEC distintos** (comparación
binaria):
- `_contribuciones_maximas(item)`: calcula el tope de puntos que un ítem puede
  aportar por campo (1 para comparación binaria, 4 para juicio situacional).
- `_contribuciones(item, respuesta)`: calcula los puntos realmente obtenidos
  por campo a partir de la respuesta concreta.
- `calcular_puntajes_escala` y `calcular_puntajes_dimension` se reescribieron
  para agregar estas contribuciones en vez de contar respuestas binarias.

**Perfil integrado:** anteriormente el "perfil dominante" se calculaba
promediando intereses y competencias en un solo número. Ahora `generar_perfil`
determina primero el **ranking de intereses** (1º, 2º y 3º lugar) y lo cruza
con el **porcentaje de competencias** de cada campo, generando una
interpretación textual preliminar y orientativa, tal como lo pide el
documento de lineamientos. Como en este sistema Intereses y Competencias son
instrumentos separados (pruebas distintas), se agregó
`_obtener_aplicacion_complementaria` para localizar automáticamente la otra
prueba ya completada por el mismo estudiante y así construir el perfil
cruzado.

Archivo: [backend/app/services/psicometrico_service.py](../backend/app/services/psicometrico_service.py).

### 3.3 Seguridad — ocultamiento de la clave de calificación

**Antes:** el endpoint `GET /instrumentos/<id>` devolvía el ítem completo,
incluyendo qué opción era la "correcta" (`valor: 1`), visible para cualquier
usuario autenticado que inspeccionara la respuesta de red.

**Después:** `Item.to_dict(incluir_clave=False)` retorna las opciones sin el
campo `puntaje`. El controlador `obtener_instrumento` decide si el usuario
autenticado puede ver la clave según su rol (bienestar, TI, investigador,
directivo la ven; estudiante no).

Archivos: [backend/app/models/instrumento.py](../backend/app/models/instrumento.py),
[backend/app/controllers/instrumento_controller.py](../backend/app/controllers/instrumento_controller.py).

### 3.4 Exportación de datos

**Antes:** solo existían dos endpoints CSV (`/exportacion/csv/resultados` y
`/exportacion/csv/estadisticas`), sin desglose por ítem ni trazabilidad.

**Después:** se agregó `GET /exportacion/excel/completo`, que genera un libro
de Excel con 6 hojas, siguiendo la "Estructura mínima de la base de datos
exportable" del documento de lineamientos:

1. **Identificación** — id_aplicacion, id_estudiante, institución, grado, grupo, edad, fecha.
2. **Aplicación** — versión de la prueba, fechas de inicio/fin, tiempo total, dispositivo.
3. **Respuestas** — código de ítem, respuesta visible/original, campo asociado, puntaje obtenido, orden del ítem, versión del ítem, estado (trazabilidad).
4. **Intereses** — puntaje por campo (R-I-A-S-E-C) y ranking RIASEC.
5. **Competencias** — puntaje y porcentaje por campo.
6. **Perfil Integrado** — campos prioritarios 1/2/3 e interpretación generada.

Archivos: [backend/app/controllers/exportacion_controller.py](../backend/app/controllers/exportacion_controller.py),
[frontend/app/routes/admin_routes.py](../frontend/app/routes/admin_routes.py),
[frontend/app/templates/admin/exportar.html](../frontend/app/templates/admin/exportar.html).
Dependencia nueva: `openpyxl` (agregada a `backend/requirements.txt`).

### 3.5 Registro demográfico

Se agregó el campo demográfico **"Grupo o Curso"** (`CampoDemografico`), que
faltaba para cumplir el registro mínimo exigido (id, grado, institución,
**grupo**, edad, fecha de aplicación).

### 3.6 Importación del banco completo del cliente

El importador [importar_banco_cliente.py](../importar_banco_cliente.py) lee las
fichas DOCX originales y valida antes de tocar la base de datos que existan 60
ítems de intereses y 64 de competencias, con códigos únicos, dos alternativas
en intereses y una clave 4-3-2-1 completa en competencias. Se ejecuta primero
con `py importar_banco_cliente.py --dry-run` y luego sin `--dry-run` para
aplicar la carga.

Las fichas de intereses con códigos internos repetidos usan el código único del
nombre de archivo como identificador técnico y conservan la ruta de origen para
trazabilidad. La carga reemplaza los ítems de ambas dimensiones; por la relación
en cascada, las respuestas asociadas a esos ítems también se eliminan.

### 3.7 Corrección de balance de ítems

Durante la migración inicial, los ítems de comparación binaria quedaron
agrupados administrativamente bajo un solo campo del par. Con el banco completo
se conserva la distribución del cliente: cada ítem se agrupa bajo una escala
existente sin alterar el campo RIASEC real de sus opciones. La calificación usa
siempre los campos definidos dentro de las opciones y normaliza cada campo con
su máximo efectivo, incluso cuando las cantidades difieren por campo.

---

## 4. Compatibilidad y limitaciones conocidas

- Los tipos de ítem anteriores (`eleccion_forzada`, `opcion_multiple`) se
  mantienen soportados en el motor de puntuación por retrocompatibilidad,
  pero ya no se usan en el banco de ítems activo.
- Los scripts de datos de prueba en la raíz del repositorio (`seed_*.py`,
  `simular_pruebas.py`, `fix_*.py`) fueron escritos para el banco de ítems
  anterior y no son compatibles con la nueva estructura; no se actualizaron
  porque son herramientas de generación de datos de ejemplo, no
  funcionalidad del producto.
- Las aplicaciones (intentos de prueba) completadas antes de esta migración
  perdieron sus respuestas individuales (por la relación en cascada entre
  ítems y respuestas), aunque los perfiles vocacionales generados
  previamente no se eliminaron.
