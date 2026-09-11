"""Importa el banco completo de ítems entregado por el cliente.

Fuente oficial:
- `data/Items Full day.xlsx`, con exactamente 30 ítems de Intereses y 30 de Competencias.

Ejemplos:
    py importar_banco_cliente.py --dry-run
    py importar_banco_cliente.py

La ejecución sin --dry-run sincroniza el banco oficial. Los ítems anteriores se desactivan para conservar el historial.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree
from openpyxl import load_workbook


RIASEC = (
    "Realista",
    "Investigativo",
    "Artístico",
    "Social",
    "Emprendedor",
    "Convencional",
)
RIASEC_NORMALIZADO = {
    "realista": "Realista",
    "investigativo": "Investigador",
    "investigador": "Investigador",
    "investigativa": "Investigador",
    "artistico": "Artístico",
    "artistica": "Artístico",
    "social": "Social",
    "emprendedor": "Emprendedor",
    "convencional": "Convencional",
}


class BancoInvalido(ValueError):
    """Indica que una ficha del cliente no cumple el formato mínimo."""


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c)).lower()


def limpiar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip()


def leer_parrafos_docx(ruta: Path) -> list[str]:
    with ZipFile(ruta) as archivo:
        raiz = ElementTree.fromstring(archivo.read("word/document.xml"))
    parrafos = []
    for nodo in raiz.iter():
        if nodo.tag.endswith("}p"):
            texto = " ".join(
                hijo.text or ""
                for hijo in nodo.iter()
                if hijo.tag.endswith("}t")
            )
            texto = limpiar(texto)
            if texto:
                parrafos.append(texto)
    return parrafos


def nombre_riasec(texto: str) -> str | None:
    clave = normalizar(texto).strip(" :()")
    return RIASEC_NORMALIZADO.get(clave)


def campo_desde_encabezado(texto: str) -> str | None:
    clave = normalizar(texto)
    for nombre, campo in RIASEC_NORMALIZADO.items():
        if re.search(rf"\bdimension\s+{re.escape(nombre)}", clave):
            return campo
    return None


def campos_marcados(parrafos: list[str]) -> list[str]:
    encontrados = []
    try:
        inicio = next(
            indice for indice, parrafo in enumerate(parrafos)
            if "campos vocacionales articulados" in normalizar(parrafo)
        )
        candidatos = parrafos[inicio + 1:inicio + 3]
    except StopIteration:
        candidatos = parrafos
    for parrafo in candidatos:
        normalizado = normalizar(parrafo)
        for campo in RIASEC:
            clave = normalizar(campo)
            if re.search(rf"{re.escape(clave)}\s*\(\s*x\s*\)", normalizado):
                campo_canonico = RIASEC_NORMALIZADO[clave]
                if campo_canonico not in encontrados:
                    encontrados.append(campo_canonico)
    return encontrados


def siguiente(parrafos: list[str], indice: int) -> str:
    if indice + 1 >= len(parrafos):
        raise BancoInvalido("falta contenido después de una etiqueta")
    return parrafos[indice + 1]


def extraer_interes(ruta: Path) -> dict:
    parrafos = leer_parrafos_docx(ruta)
    normalizados = [normalizar(p) for p in parrafos]
    campos = campos_marcados(parrafos)

    try:
        indice_codigo = next(i for i, p in enumerate(normalizados) if p == "codigo del item")
    except StopIteration as exc:
        raise BancoInvalido(f"{ruta.name}: no contiene código") from exc
    codigo_documento = siguiente(parrafos, indice_codigo)
    codigo_archivo = re.sub(r"\s+", "", ruta.stem).upper()
    if not re.fullmatch(r"[A-Z]{4}\d+", codigo_archivo):
        raise BancoInvalido(f"{ruta.name}: nombre de archivo sin código válido")

    opciones = {}
    for letra in ("A", "B"):
        etiqueta = normalizar(f"Opción {letra}")
        try:
            indice = next(i for i, p in enumerate(normalizados) if p == etiqueta)
        except StopIteration as exc:
            raise BancoInvalido(f"{ruta.name}: falta Opción {letra}") from exc
        campo_texto = siguiente(parrafos, indice)
        campo_match = re.search(r"campo\s*:\s*(.+)", campo_texto, re.IGNORECASE)
        if campo_match and campo_match.group(1).strip():
            campo = nombre_riasec(campo_match.group(1))
            texto = siguiente(parrafos, indice + 1)
        else:
            posicion_campo = 0 if letra == "A" else 1
            campo = campos[posicion_campo] if len(campos) > posicion_campo else None
            texto = siguiente(parrafos, indice + 1)
            if normalizar(texto).startswith("campo"):
                texto = siguiente(parrafos, indice + 2)
        if not campo:
            raise BancoInvalido(f"{ruta.name}: campo inválido en Opción {letra}")
        opciones[letra] = {"campo": campo, "texto": texto}

    try:
        indice_enunciado = next(i for i, p in enumerate(normalizados) if p.startswith("enunciado:"))
    except StopIteration as exc:
        raise BancoInvalido(f"{ruta.name}: falta ENUNCIADO") from exc
    texto = siguiente(parrafos, indice_enunciado)
    if len(campos) < 2:
        campos = list(dict.fromkeys([opciones["A"]["campo"], opciones["B"]["campo"]]))
    if len(campos) != 2 or {opciones["A"]["campo"], opciones["B"]["campo"]} != set(campos):
        raise BancoInvalido(f"{ruta.name}: los campos declarados no coinciden con las opciones")

    return {
        "codigo": codigo_archivo,
        "codigo_documento": codigo_documento,
        "texto": texto,
        "contexto": None,
        "tipo": "comparacion_binaria",
        "opciones": {
            "opcion_a": opciones["A"],
            "opcion_b": opciones["B"],
        },
        "campo_escala": opciones["A"]["campo"],
        "fuente": str(ruta),
    }


def extraer_competencia(ruta: Path) -> list[dict]:
    parrafos = leer_parrafos_docx(ruta)
    normalizados = [normalizar(p) for p in parrafos]
    inicios = []
    for indice, parrafo in enumerate(parrafos):
        coincidencia = re.search(
            r"^DIMENSI[ÓO]N\b.*?(?:\|\s*)?([A-Z]{3})-\s*(\d)\s*(\d)$",
            parrafo,
            re.IGNORECASE,
        )
        if coincidencia:
            inicios.append((indice, f"{coincidencia.group(1).upper()}-{coincidencia.group(2)}{coincidencia.group(3)}"))
    if not inicios:
        raise BancoInvalido(f"{ruta.name}: no contiene encabezados de ítems")

    items = []
    for posicion, (inicio, codigo) in enumerate(inicios):
        fin = inicios[posicion + 1][0] if posicion + 1 < len(inicios) else len(parrafos)
        bloque = parrafos[inicio:fin]
        normales = normalizados[inicio:fin]

        def indice_de(etiqueta: str) -> int:
            try:
                return next(i for i, p in enumerate(normales) if p == normalizar(etiqueta))
            except StopIteration as exc:
                raise BancoInvalido(f"{codigo}: falta '{etiqueta}'") from exc

        def indice_que_comienza(etiqueta: str) -> int:
            try:
                return next(i for i, p in enumerate(normales) if p.startswith(normalizar(etiqueta)))
            except StopIteration as exc:
                raise BancoInvalido(f"{codigo}: falta '{etiqueta}'") from exc

        indice_campo = indice_que_comienza("Campo vocacional articulador")
        campo = nombre_riasec(siguiente(bloque, indice_campo))
        if not campo:
            campo = campo_desde_encabezado(bloque[0])
        if not campo:
            raise BancoInvalido(f"{codigo}: campo RIASEC inválido")

        indice_contexto = indice_que_comienza("Contexto de la situación")
        indice_enunciado = indice_que_comienza("Enunciado del ítem")
        contexto = siguiente(bloque, indice_contexto)
        texto = siguiente(bloque, indice_enunciado)

        opciones = []
        for letra in "ABCD":
            etiqueta = normalizar(f"Opción {letra}")
            try:
                indice_opcion = next(i for i, p in enumerate(normales) if p == etiqueta)
            except StopIteration as exc:
                raise BancoInvalido(f"{codigo}: falta Opción {letra}") from exc
            opciones.append({"letra": letra, "texto": siguiente(bloque, indice_opcion)})

        indice_clave = indice_de("Nivel de respuesta")
        puntajes = {}
        for indice in range(indice_clave + 1, len(bloque) - 1):
            letra = bloque[indice + 1].upper()
            if bloque[indice] in {"1", "2", "3", "4"} and re.fullmatch(r"[ABCD]", letra):
                puntajes[letra] = int(bloque[indice])
        if set(puntajes) != set("ABCD") or set(puntajes.values()) != {1, 2, 3, 4}:
            raise BancoInvalido(f"{codigo}: la clave no contiene 4, 3, 2 y 1 exactamente una vez")
        for opcion in opciones:
            opcion["puntaje"] = puntajes[opcion["letra"]]

        items.append({
            "codigo": codigo,
            "texto": texto,
            "contexto": contexto,
            "tipo": "juicio_situacional",
            "opciones": {"opciones": opciones},
            "campo_escala": campo,
            "fuente": str(ruta),
        })
    return items


def _valor_fila(row, headers, clave):
    idx = headers.index(clave)
    return row[idx] if idx < len(row) else None


def _parsear_intereses_pdf(ruta_pdf: Path) -> list[dict]:
    """Genera el esquema de 30 intereses compatibilizado con el banco del cliente
    a partir de la estructura del PDF Intereses.pdf del repositorio."""
    import pymupdf

    if not ruta_pdf.exists():
        raise BancoInvalido(f'No existe el PDF de intereses: {ruta_pdf}')

    doc = pymupdf.open(str(ruta_pdf))
    texto_total = '\n'.join(page.get_text('text') for page in doc)
    bloques = [bloque.strip() for bloque in re.split(r'\n(?=Ítem \d+ ·)', texto_total) if bloque.strip()]

    # El primer bloque es el encabezado del PDF; se descarta automáticamente.
    intereses = []
    for bloque in bloques:
        if not bloque.startswith('Ítem'):
            continue
        lines = [line.strip() for line in bloque.splitlines() if line.strip()]
        if not lines:
            continue
        header = lines[0]
        m_header = re.search(r'Ítem\s+\d+\s+·\s*([A-Z0-9]+)\s*·\s*([^–\n]+?)\s*–\s*([^\n]+)', header)
        if not m_header:
            continue
        codigo = m_header.group(1).strip()
        campo_a = limpiar(m_header.group(2).strip())
        campo_b = limpiar(m_header.group(3).strip())
        campo_a_norm = nombre_riasec(campo_a) or campo_a
        campo_b_norm = nombre_riasec(campo_b) or campo_b

        # Texto del enunciado: todo lo que está antes de la marca de Opción A.
        option_a_idx = next((i for i, l in enumerate(lines) if l.startswith('Opción A ·')), None)
        if option_a_idx is None:
            continue
        texto_lines = lines[1:option_a_idx]
        texto = limpiar(' '.join(texto_lines))

        option_b_idx = next((i for i, l in enumerate(lines) if l.startswith('Opción B ·')), None)
        if option_b_idx is None:
            continue
        option_a_text_lines = lines[option_a_idx + 1:option_b_idx]
        option_b_text_lines = lines[option_b_idx + 1:]
        # Hay una marca final 'Puntúa' en la misma línea o a continuación; quitarla.
        option_b_text_lines = [l for l in option_b_text_lines if not l.startswith('Puntúa:')]
        campo_a_text = limpiar(' '.join(option_a_text_lines))
        campo_b_text = limpiar(' '.join(option_b_text_lines))

        intereses.append({
            'codigo': codigo,
            'codigo_documento': codigo,
            'texto': texto,
            'contexto': None,
            'tipo': 'comparacion_binaria',
            'opciones': {
                'opcion_a': {'campo': campo_a_norm, 'texto': campo_a_text},
                'opcion_b': {'campo': campo_b_norm, 'texto': campo_b_text},
            },
            'campo_escala': campo_a_norm,
            'fuente': str(ruta_pdf),
        })

    if len(intereses) != 30:
        raise BancoInvalido(f'Se esperaban 30 intereses y se encontraron {len(intereses)}')
    return intereses


def _parsear_competencias_pdf(ruta_pdf: Path) -> list[dict]:
    """Genera el esquema de 30 competencias compatible con el exportador
    del cliente a partir de la estructura textual del PDF Competencias.pdf."""
    import pymupdf

    if not ruta_pdf.exists():
        raise BancoInvalido(f'No existe el PDF de competencias: {ruta_pdf}')

    doc = pymupdf.open(str(ruta_pdf))
    texto_total = '\n'.join(page.get_text('text') for page in doc)
    bloques = [bloque.strip() for bloque in re.split(r'\n(?=Ítem \d+ ·)', texto_total) if bloque.strip()]

    competencias = []
    for bloque in bloques:
        if not bloque.startswith('Ítem'):
            continue
        lines = [line.strip() for line in bloque.splitlines() if line.strip()]
        if not lines:
            continue
        header = lines[0]
        m_header = re.search(r'Ítem\s+\d+\s+·\s*([A-Z0-9-]+)\s*·\s*([^·\n]+)\s*·\s*([^\n]+)', header)
        if not m_header:
            continue
        codigo = m_header.group(1).strip()
        campo = limpiar(m_header.group(2).strip())
        habilidad = limpiar(m_header.group(3).strip())
        campo_norm = nombre_riasec(campo) or campo

        context_start = next((i for i, l in enumerate(lines) if l.startswith('Contexto:')), None)
        if context_start is None:
            continue
        # El enunciado nos llega en la línea de texto que sigue al contexto y precede a A. (
        # en la extracción del texto PDF. Por eso tomamos ese segmento de líneas.
        option_a_line_index = next((i for i, l in enumerate(lines) if l.startswith('A. (')), None)
        if option_a_line_index is None:
            continue
        # Tomamos el texto del contexto desde la primera línea de contexto hasta el inicio del
        # enunciado, guardando el texto completo de la situación.
        # El primer enunciado suele aparecer como la última línea antes de la opción A.
        enunciado_lines = []
        question_line_idx = None
        for i in range(context_start + 1, option_a_line_index):
            if lines[i].startswith('Demanda cognitiva:') or lines[i].startswith('Dificultad:'):
                continue
            if lines[i].startswith('A.'):
                continue
            if lines[i].startswith('B.') or lines[i].startswith('C.') or lines[i].startswith('D.'):
                continue
            # La línea de context y las líneas continuadas se dejan en contexto, el enunciado
            # es la última línea antes de las opciones. Si ya no hay contexto papel, se toma como
            # enunciado la línea con la pregunta / situación.
            if 'Ante esta situación' in lines[i] or 'consideras cómo' in lines[i] or 'respuesta' in lines[i].lower():
                question_line_idx = i
            enunciado_lines.append(lines[i])

        contexto_lines = []
        for i in range(context_start + 1, option_a_line_index):
            if 'Ante esta situación' in lines[i] or 'consideras cómo' in lines[i]:
                break
            contexto_lines.append(lines[i])

        # Si el contexto ocupa varias líneas, usar solo el bloque de contexto y descartar la línea de
        # enunciado que empieza con 'Ante esta situación' o similar.
        texto = ' '.join([l for l in lines[context_start + 1:option_a_line_index] if not l.startswith('Contexto:')])
        # La verdadera pregunta de la competencia es el enunciado lineal mínimo entre contexto y elección.
        texto = texto.split('Ante esta situación')[0] if 'Ante esta situación' in texto else texto
        # Pero la pregunta se observa mejor como texto del bloque siguiente; si hay una frase con 'Ante', se usa.
        pregunta = ''
        for i in range(context_start + 1, option_a_line_index):
            if 'Ante esta situación' in lines[i] or 'consideras cómo' in lines[i]:
                pregunta = lines[i]
                break
        if pregunta:
            texto = pregunta

        # Opción texto y puntajes A-D, en el orden del PDF.
        opciones = []
        letter_points = []
        for i, l in enumerate(lines):
            m = re.match(r'^([A-D])\. \((\d+) pts\)', l)
            if m:
                letter_points.append((m.group(1), int(m.group(2)), i))

        for idx, (letra, pts, idx_line) in enumerate(letter_points):
            # Las opciones están en las líneas a continuación de la etiqueta de la opción.
            fin = letter_points[idx + 1][2] if idx + 1 < len(letter_points) else len(lines)
            texto_op_lines = lines[idx_line + 1:fin]
            # if '# Mejor respuesta' appears on label line? remove it from all lines.
            texto_op = limpiar(' '.join(texto_op_lines))
            texto_op = texto_op.replace('# Mejor respuesta', '').replace('reemplazando', '').replace('mejor', '')
            texto_op = limpiar(texto_op)
            opciones.append({'letra': letra, 'texto': texto_op, 'puntaje': pts})

        competencias.append({
            'codigo': codigo,
            'texto': texto,
            'contexto': limpiar(' '.join(contexto_lines)) if contexto_lines else '',
            'tipo': 'juicio_situacional',
            'opciones': {'opciones': opciones},
            'campo_escala': campo_norm,
            'fuente': str(ruta_pdf),
        })

    if len(competencias) != 30:
        raise BancoInvalido(f'Se esperaban 30 competencias y se encontraron {len(competencias)}')
    return competencias


def cargar_banco_desde_pdfs(ruta_intereses: Path | str, ruta_competencias: Path | str) -> tuple[list[dict], list[dict]]:
    """Carga el banco de prueba desde los PDFs de Intereses y Competencias."""
    intereses = _parsear_intereses_pdf(Path(ruta_intereses))
    competencias = _parsear_competencias_pdf(Path(ruta_competencias))
    return intereses, competencias


def cargar_banco_desde_excel(ruta_excel: Path | str) -> tuple[list[dict], list[dict]]:
    """Carga 30 intereses y 30 competencias desde el Excel de dos hojas.

    El valor devuelto conserva el mismo formato de salida que el importer
    existente para que el flujo de "importar_en_bd" pueda seguir inyectando
    filas dentro del esquema actual del proyecto.
    """
    ruta = Path(ruta_excel)
    if not ruta.exists():
        raise BancoInvalido(f"No existe el archivo Excel: {ruta}")

    wb = load_workbook(filename=ruta, data_only=True)
    if 'Intereses' not in wb.sheetnames or 'Competencias' not in wb.sheetnames:
        raise BancoInvalido("El Excel debe contener las hojas 'Intereses' y 'Competencias'.")

    ws_intereses = wb['Intereses']
    ws_competencias = wb['Competencias']

    # --- Hoja Intereses: 30 filas, columnas del contrato oficial ---
    headers_i = [c.value for c in ws_intereses[1]]
    intereses = []
    for row in ws_intereses.iter_rows(min_row=2, values_only=True):
        if not any(cell is not None and str(cell).strip() for cell in row):
            continue
        fila = dict(zip(headers_i, row))
        codigo = str(fila.get('ID', '')).strip()
        texto = str(fila.get('Enunciado', '')).strip()
        opcion_a = str(fila.get('Opción A', '')).strip()
        opcion_b = str(fila.get('Opción B', '')).strip()
        campo_a = str(fila.get('Campo A', '')).strip()
        campo_b = str(fila.get('Campo B', '')).strip()
        if not codigo or not texto or not opcion_a or not opcion_b:
            continue
        # campo_escala se deriva de la primera opción del contrato de extracción original
        campo_escala = nombre_riasec(campo_a) or campo_a
        if not campo_escala:
            raise BancoInvalido(f"Campo A inválido en interés {codigo}")
        intereses.append({
            'codigo': codigo,
            'codigo_documento': codigo,
            'texto': texto,
            'contexto': None,
            'tipo': 'comparacion_binaria',
            'opciones': {
                'opcion_a': {'campo': nombre_riasec(campo_a) or campo_a, 'texto': opcion_a},
                'opcion_b': {'campo': nombre_riasec(campo_b) or campo_b, 'texto': opcion_b},
            },
            'campo_escala': campo_escala,
            'fuente': str(ruta),
        })

    # --- Hoja Competencias: 30 filas, columnas del contrato oficial ---
    headers_c = [c.value for c in ws_competencias[1]]
    competencias = []
    for row in ws_competencias.iter_rows(min_row=2, values_only=True):
        if not any(cell is not None and str(cell).strip() for cell in row):
            continue
        fila = dict(zip(headers_c, row))
        codigo = str(fila.get('ID', '')).strip()
        campo = str(fila.get('Campo', '')).strip()
        contexto = str(fila.get('Contexto', '')).strip()
        texto = str(fila.get('Enunciado', '')).strip()
        op_a = str(fila.get('Opción A', '')).strip()
        op_b = str(fila.get('Opción B', '')).strip()
        op_c = str(fila.get('Opción C', '')).strip()
        op_d = str(fila.get('Opción D', '')).strip()
        pt_a = fila.get('Pt A')
        pt_b = fila.get('Pt B')
        pt_c = fila.get('Pt C')
        pt_d = fila.get('Pt D')
        if not codigo or not campo or not texto:
            continue
        opciones = []
        for letra, texto_op, puntaje in (
            ('A', op_a, pt_a),
            ('B', op_b, pt_b),
            ('C', op_c, pt_c),
            ('D', op_d, pt_d),
        ):
            if texto_op:
                opciones.append({'letra': letra, 'texto': texto_op, 'puntaje': int(puntaje) if puntaje is not None else 1})
        competencias.append({
            'codigo': codigo,
            'texto': texto,
            'contexto': contexto,
            'tipo': 'juicio_situacional',
            'opciones': {'opciones': opciones},
            'campo_escala': nombre_riasec(campo) or campo,
            'fuente': str(ruta),
        })

    if len(intereses) != 30:
        raise BancoInvalido(f"Se esperaban 30 intereses y se encontraron {len(intereses)}")
    if len(competencias) != 30:
        raise BancoInvalido(f"Se esperaban 30 competencias y se encontraron {len(competencias)}")

    codigos = [item['codigo'] for item in intereses + competencias]
    repetidos = sorted({codigo for codigo in codigos if codigos.count(codigo) > 1})
    if repetidos:
        raise BancoInvalido(f"Códigos repetidos: {', '.join(repetidos)}")

    return intereses, competencias


def cargar_banco(intereses_dir: Path, competencias_docx: Path) -> tuple[list[dict], list[dict]]:
    intereses = [extraer_interes(ruta) for ruta in sorted(intereses_dir.glob("*/*.docx"))]
    competencias = extraer_competencia(competencias_docx)
    if len(intereses) != 60:
        raise BancoInvalido(f"Se esperaban 60 intereses y se encontraron {len(intereses)}")
    if len(competencias) != 64:
        raise BancoInvalido(f"Se esperaban 64 competencias y se encontraron {len(competencias)}")
    codigos = [item["codigo"] for item in intereses + competencias]
    repetidos = sorted({codigo for codigo in codigos if codigos.count(codigo) > 1})
    if repetidos:
        raise BancoInvalido(f"Códigos repetidos: {', '.join(repetidos)}")
    return intereses, competencias


def argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    base = Path(__file__).resolve().parents[2]
    parser.add_argument(
        "--excel",
        type=Path,
        default=base / "data" / "Items Full day.xlsx",
    )
    parser.add_argument(
        "--intereses-dir",
        type=Path,
        default=base / "ITEMS-20260902T152002Z-1-001" / "ITEMS",
    )
    parser.add_argument(
        "--competencias-docx",
        type=Path,
        default=base / "Items Juicio situacional.docx",
    )
    parser.add_argument("--version", default="2.0")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def importar_en_bd(intereses: list[dict], competencias: list[dict], version: str) -> None:
    root = Path(__file__).resolve().parents[2]
    backend_dir = root / 'backend'
    sys.path.insert(0, str(backend_dir))
    from app import create_app

    app = create_app()
    with app.app_context():
        from app.extensions import db
        from app.models.demografico import CampoDemografico
        from app.models.instrumento import Dimension, Escala, Item

        dimension_intereses = Dimension.query.filter(Dimension.nombre.ilike("%interes%"),).first()
        dimension_competencias = Dimension.query.filter(Dimension.nombre.ilike("%competencia%"),).first()
        if not dimension_intereses or not dimension_competencias:
            raise BancoInvalido("No se encontraron las dimensiones de Intereses y Competencias")

        escalas_intereses = {escala.nombre: escala for escala in dimension_intereses.escalas}
        escalas_competencias = {escala.nombre: escala for escala in dimension_competencias.escalas}
        faltantes = sorted(
            ({item["campo_escala"] for item in intereses} - set(escalas_intereses))
            | ({item["campo_escala"] for item in competencias} - set(escalas_competencias))
        )
        if faltantes:
            raise BancoInvalido(f"No existen escalas para: {', '.join(faltantes)}")

        # Mantener trazabilidad: los ítems anteriores se desactivan, no se borran.
        escala_ids = [e.id for d in (dimension_intereses, dimension_competencias) for e in d.escalas]
        Item.query.filter(Item.escala_id.in_(escala_ids)).update(
            {Item.activo: False}, synchronize_session=False
        )

        for escala in dimension_intereses.escalas:
            escala.valor_minimo, escala.valor_maximo = 0, 1
        for escala in dimension_competencias.escalas:
            escala.valor_minimo, escala.valor_maximo = 1, 4

        def upsert(datos, escala, orden):
            item = Item.query.filter_by(escala_id=escala.id, codigo=datos["codigo"]).first()
            if item is None:
                item = Item(escala_id=escala.id, codigo=datos["codigo"])
                db.session.add(item)
            item.texto = datos["texto"]
            item.contexto = datos["contexto"]
            item.tipo = datos["tipo"]
            item.opciones = datos["opciones"]
            item.obligatorio = True
            item.orden = orden
            item.version = version
            item.activo = True

        for orden, datos in enumerate(intereses, 1):
            upsert(datos, escalas_intereses[datos["campo_escala"]], orden)
        for orden, datos in enumerate(competencias, 1):
            upsert(datos, escalas_competencias[datos["campo_escala"]], orden)

        db.session.flush()
        activos_intereses = Item.query.join(Escala).filter(
            Escala.dimension_id == dimension_intereses.id, Item.activo == True
        ).count()
        activos_competencias = Item.query.join(Escala).filter(
            Escala.dimension_id == dimension_competencias.id, Item.activo == True
        ).count()
        if activos_intereses != 30 or activos_competencias != 30:
            db.session.rollback()
            raise BancoInvalido(
                f'Postcondición inválida: intereses={activos_intereses}, competencias={activos_competencias}'
            )

        if not CampoDemografico.query.filter_by(nombre="grupo").first():
            orden = db.session.query(db.func.max(CampoDemografico.orden)).scalar() or 0
            db.session.add(CampoDemografico(
                nombre="grupo", etiqueta="Grupo o Curso", tipo_campo="texto",
                obligatorio=False, orden=orden + 1,
            ))
        db.session.commit()
        print("Importación aplicada: 30 intereses y 30 competencias.")


def main() -> int:
    args = argumentos()
    try:
        if not args.excel or not args.excel.exists():
            raise BancoInvalido(f"No se encontró el banco oficial: {args.excel}")
        intereses, competencias = cargar_banco_desde_excel(args.excel)
        print(f"Excel oficial leído: {args.excel}")
    except (OSError, KeyError, ValueError, BancoInvalido) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Intereses validados: {len(intereses)}")
    print(f"Competencias validadas: {len(competencias)}")
    print(f"Códigos únicos: {len({item['codigo'] for item in intereses + competencias})}")
    if args.dry_run:
        print("Dry-run: no se modificó la base de datos.")
        return 0
    importar_en_bd(intereses, competencias, args.version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
