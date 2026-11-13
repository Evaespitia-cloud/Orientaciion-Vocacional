"""Filas del informe PDF: cada pregunta con la letra elegida y lo que valió.

En Intereses (comparación binaria) el campo de la pregunta es siempre el de la
opción A, así que la "luz" se enciende cuando el estudiante eligió A (1 punto
para ese campo) y queda apagada cuando eligió B (el punto fue al otro campo).
En Competencias (juicio situacional) cada letra vale entre 1 y 4 puntos, y la
letra no dice el valor: se guarda el puntaje real de la opción elegida.
"""


def enunciado_corto(texto, limite=70):
    """Inicio del enunciado en una línea, cortado en una palabra completa."""
    texto = ' '.join((texto or '').split())
    if len(texto) <= limite:
        return texto
    return texto[:limite].rsplit(' ', 1)[0].rstrip(',;:') + '…'


def fila_respuesta(numero, item, valor):
    """Fila del informe para un ítem y el valor guardado en Respuesta.valor
    (índice de la opción elegida, o None si no respondió)."""
    base = {
        'numero': numero,
        'enunciado': enunciado_corto(item.texto),
        'area': item.escala.nombre if item.escala else '',
    }

    if item.tipo == 'comparacion_binaria':
        if valor is None:
            return dict(base, tipo='luz', letra='—', valor=0, maximo=1)
        elegido = int(valor)
        return dict(base, tipo='luz', letra='A' if elegido == 0 else 'B',
                    valor=1 if elegido == 0 else 0, maximo=1)

    ops = item.opciones if isinstance(item.opciones, dict) else {}
    opciones = [o for o in ops.get('opciones', []) if isinstance(o, dict)]
    maximo = max((int(o.get('puntaje', 0)) for o in opciones), default=4) or 4
    try:
        idx = int(valor)
    except (TypeError, ValueError):
        return dict(base, tipo='cuadros', letra='—', valor=0, maximo=maximo)
    if not 0 <= idx < len(opciones):
        return dict(base, tipo='cuadros', letra='—', valor=0, maximo=maximo)
    elegida = opciones[idx]
    return dict(base, tipo='cuadros', letra=elegida.get('letra') or 'ABCD'[idx],
                valor=int(elegida.get('puntaje', 0)), maximo=maximo)


def filas_de_aplicacion(aplicacion):
    """Filas de todas las preguntas activas del instrumento de la aplicación,
    en el orden del banco, con la respuesta que dio el estudiante."""
    from ..models.aplicacion import Respuesta

    items = []
    for dimension in aplicacion.configuracion.instrumento.dimensiones:
        for escala in dimension.escalas:
            items.extend(escala.items.filter_by(activo=True).all())
    items.sort(key=lambda i: (i.orden or 0, i.id))

    valores = {r.item_id: r.valor for r in Respuesta.query.filter_by(aplicacion_id=aplicacion.id)}
    return [fila_respuesta(n, item, valores.get(item.id)) for n, item in enumerate(items, start=1)]


def _entero(x):
    """Redondeo .5 hacia arriba, como el filtro round de Jinja en la página."""
    return int(x + 0.5)


def porcentajes_area(d):
    """(combinado, intereses, competencias) en % para un campo, con el mismo
    cálculo de la página de resultados: el combinado suma los puntos de las dos
    pruebas sobre la suma de sus máximos. None si esa prueba no se presentó."""
    d = d or {}
    ip, im = d.get('interes_puntaje') or 0, d.get('interes_maximo') or 0
    cp, cm = d.get('competencia_puntaje') or 0, d.get('competencia_maximo') or 0
    intereses = _entero(ip / im * 100) if im else None
    competencias = _entero(cp / cm * 100) if cm else None
    combinado = _entero((ip + cp) / (im + cm) * 100) if (im + cm) else 0
    return combinado, intereses, competencias
