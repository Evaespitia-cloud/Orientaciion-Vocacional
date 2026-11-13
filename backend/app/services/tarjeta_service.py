"""Carta para compartir el resultado, al estilo de las de 12axes.

Dos formatos:
- ``historia``: 1080×1920, para estados de WhatsApp e historias de Instagram.
- ``enlace``: 1200×630, la vista previa que muestran las apps al pegar el enlace.

El enlace público lleva solo el perfil y los seis porcentajes, firmados con
HMAC para que nadie pueda inventar un resultado. No lleva nombre ni nada que
identifique al estudiante; el nombre solo se dibuja en la descarga si el propio
estudiante lo pide.
"""

import base64
import hashlib
import hmac
import io
import os

from flask import current_app
from PIL import Image, ImageDraw, ImageFont

from .psicometrico_service import PERFILES_HOLLAND, programas_usb

RECURSOS = os.path.join(os.path.dirname(__file__), '..', 'recursos')
AREAS = ['Realista', 'Investigador', 'Artístico', 'Social', 'Emprendedor', 'Convencional']
LETRA = {'Realista': 'R', 'Investigador': 'I', 'Artístico': 'A', 'Social': 'S', 'Emprendedor': 'E', 'Convencional': 'C'}
POR_LETRA = {v: k for k, v in LETRA.items()}
COLOR = {'Realista': '#eb6834', 'Investigador': '#2a78d6', 'Artístico': '#e87ba4',
         'Social': '#1baf7a', 'Emprendedor': '#eda100', 'Convencional': '#4a3aa7'}
TINTA, PAPEL = '#1c1b22', '#fdfaf6'
ARCHIVO_ZORRO = {'Realista': 'realista', 'Investigador': 'investigador', 'Artístico': 'artistico',
                 'Social': 'social', 'Emprendedor': 'emprendedor', 'Convencional': 'convencional'}


# ─── Enlace firmado ───────────────────────────────────────────────────────── #

def _firma(cuerpo):
    clave = current_app.config['SECRET_KEY'].encode()
    digest = hmac.new(clave, cuerpo.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest[:9]).decode().rstrip('=')


def crear_codigo(codigo_riasec, porcentajes):
    """"RCI-63-52-63-60-43-63" + firma. Los porcentajes van en orden RIASEC."""
    cuerpo = '-'.join([codigo_riasec] + [str(int(round(porcentajes.get(a, 0)))) for a in AREAS])
    return f'{cuerpo}.{_firma(cuerpo)}'


def leer_codigo(codigo):
    """Devuelve (codigo_riasec, porcentajes) o None si la firma no cuadra."""
    try:
        cuerpo, firma = codigo.rsplit('.', 1)
        partes = cuerpo.split('-')
        if len(partes) != 7 or not hmac.compare_digest(firma, _firma(cuerpo)):
            return None
        letras = partes[0]
        if not 1 <= len(letras) <= 3 or any(l not in POR_LETRA for l in letras):
            return None
        valores = [int(v) for v in partes[1:]]
        if any(not 0 <= v <= 100 for v in valores):
            return None
        return letras, dict(zip(AREAS, valores))
    except (ValueError, KeyError):
        return None


def perfiles_de(codigo_riasec):
    principal = POR_LETRA[codigo_riasec[0]]
    secundario = POR_LETRA[codigo_riasec[1]] if len(codigo_riasec) > 1 else None
    return principal, secundario


# ─── Dibujo ───────────────────────────────────────────────────────────────── #

def titulo(tamano, peso=900):
    """Red Hat Display (eje único: peso)."""
    f = ImageFont.truetype(os.path.join(RECURSOS, 'fuentes', 'RedHatDisplay.ttf'), tamano)
    f.set_variation_by_axes([peso])
    return f


def texto(tamano, peso=500):
    """Inter (ejes: tamaño óptico y peso)."""
    f = ImageFont.truetype(os.path.join(RECURSOS, 'fuentes', 'Inter.ttf'), tamano)
    f.set_variation_by_axes([min(32, max(14, tamano // 2)), peso])
    return f


def _rgb(hex_):
    h = hex_.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _mezcla(a, b, t):
    a, b = _rgb(a), _rgb(b)
    return tuple(round(a[i] * (1 - t) + b[i] * t) for i in range(3))


def _tinta_sobre(hex_):
    r, g, b = _rgb(hex_)
    return TINTA if (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255 > 0.6 else '#ffffff'


def zorro(perfil):
    """El zorro en acción del perfil; si todavía no existe, el de disfraz o el de siempre."""
    base = os.path.join(RECURSOS, 'mascota')
    for nombre in (f'{ARCHIVO_ZORRO.get(perfil, "")}-accion.png', f'{ARCHIVO_ZORRO.get(perfil, "")}.png', 'default.png'):
        ruta = os.path.join(base, nombre)
        if os.path.exists(ruta):
            return Image.open(ruta).convert('RGBA')
    return None


def _ajustar(img, ancho, alto):
    """Escala para caber en la caja, agrandando si hace falta (thumbnail solo achica)."""
    escala = min(ancho / img.width, alto / img.height)
    return img.resize((max(1, round(img.width * escala)), max(1, round(img.height * escala))), Image.LANCZOS)


def _texto_ajustado(draw, xy, txt, fuente_fn, tamano, ancho_max, color, peso=None, minimo=24):
    t = tamano
    while t > minimo:
        f = fuente_fn(t) if peso is None else fuente_fn(t, peso)
        if draw.textlength(txt, font=f) <= ancho_max:
            break
        t -= 4
    draw.text(xy, txt, font=f, fill=color)
    return f


def _barras(draw, x, y, ancho, porcentajes, fuente_area, fuente_pct, alto_fila, grosor, color_texto, fondo_barra):
    orden = sorted(AREAS, key=lambda a: -porcentajes.get(a, 0))
    for i, area in enumerate(orden):
        fy = y + i * alto_fila
        v = porcentajes.get(area, 0)
        draw.text((x, fy), area, font=fuente_area, fill=color_texto)
        etiqueta = f'{int(round(v))} %'
        draw.text((x + ancho - draw.textlength(etiqueta, font=fuente_pct), fy), etiqueta, font=fuente_pct, fill=color_texto)
        by = fy + fuente_area.size + 12
        draw.rounded_rectangle([x, by, x + ancho, by + grosor], radius=grosor // 2, fill=fondo_barra)
        largo = max(grosor, int(ancho * v / 100))
        draw.rounded_rectangle([x, by, x + largo, by + grosor], radius=grosor // 2, fill=COLOR[area])


def dibujar_historia(codigo_riasec, porcentajes, nombre=None, sitio=''):
    principal, secundario = perfiles_de(codigo_riasec)
    W, H = 1080, 1920
    color = COLOR[principal]
    img = Image.new('RGB', (W, H), color)
    d = ImageDraw.Draw(img)
    claro = _tinta_sobre(color)
    suave = _mezcla(color, '#ffffff', 0.22) if claro == '#ffffff' else _mezcla(color, TINTA, 0.12)

    # Círculo de fondo detrás del zorro
    d.ellipse([W - 760, 300, W + 200, 1260], fill=suave)

    m = 80
    d.text((m, 92), 'MI PERFIL VOCACIONAL', font=texto(30, 700), fill=claro)
    logo = Image.open(os.path.join(RECURSOS, 'logo-usb.png')).convert('RGBA')
    logo = _ajustar(logo, 220, 70)
    pastilla = Image.new('RGBA', (logo.width + 36, logo.height + 24), (255, 255, 255, 255))
    pastilla.paste(logo, (18, 12), logo)
    mascara = Image.new('L', pastilla.size, 0)
    ImageDraw.Draw(mascara).rounded_rectangle([0, 0, pastilla.width - 1, pastilla.height - 1], radius=18, fill=255)
    img.paste(pastilla, (W - m - pastilla.width, 72), mascara)
    if nombre:
        d.text((m, 140), nombre, font=texto(34, 500), fill=claro)

    # El zorro en acción, grande
    z = zorro(principal)
    if z:
        z = _ajustar(z, 600, 590)
        img.paste(z, (W - z.width - 50, 1090 - z.height), z)

    _texto_ajustado(d, (m, 230), principal, titulo, 150, W - 2 * m, claro)
    info = PERFILES_HOLLAND.get(principal, {})
    d.text((m, 410), f'Código {codigo_riasec}' + (f' · Secundario: {secundario}' if secundario else ''), font=texto(36, 600), fill=claro)
    frase = (info.get('descripcion') or '').split('.')[0]
    if frase:
        y, linea, palabras = 480, '', frase.split()
        fuente_frase = texto(32, 450)
        for p in palabras:
            prueba = (linea + ' ' + p).strip()
            if d.textlength(prueba, font=fuente_frase) > 440:
                d.text((m, y), linea, font=fuente_frase, fill=claro)
                y, linea = y + 44, p
                if y > 700:
                    break
            else:
                linea = prueba
        if linea and y <= 700:
            d.text((m, y), linea + '.', font=fuente_frase, fill=claro)

    # Tarjeta blanca con las barras y los programas
    top = 1110
    d.rounded_rectangle([m - 20, top, W - m + 20, top + 700], radius=36, fill=PAPEL)
    d.text((m + 20, top + 40), 'Tus seis campos', font=texto(28, 700), fill='#8a8698')
    _barras(d, m + 20, top + 92, W - 2 * m - 40, porcentajes, texto(30, 600), texto(30, 700), 62, 16, TINTA, '#ecebf0')
    py = top + 92 + 6 * 62 + 16
    d.line([m + 20, py, W - m - 20, py], fill='#e5e3ea', width=2)
    d.text((m + 20, py + 26), 'Programas de la USB que encajan contigo', font=texto(28, 700), fill='#8a8698')
    for i, prog in enumerate(programas_usb(principal)[:3]):
        _texto_ajustado(d, (m + 20, py + 74 + i * 46), '· ' + prog['nombre'], texto, 32, W - 2 * m - 40, TINTA, 550)

    pie = 'Descubre el tuyo' + (f' en {sitio}' if sitio else '')
    f_pie = texto(32, 700)
    d.text(((W - d.textlength(pie, font=f_pie)) / 2, H - 80), pie, font=f_pie, fill=claro)
    return img


def dibujar_enlace(codigo_riasec, porcentajes, sitio=''):
    principal, secundario = perfiles_de(codigo_riasec)
    W, H = 1200, 630
    color = COLOR[principal]
    img = Image.new('RGB', (W, H), color)
    d = ImageDraw.Draw(img)
    claro = _tinta_sobre(color)
    suave = _mezcla(color, '#ffffff', 0.22) if claro == '#ffffff' else _mezcla(color, TINTA, 0.12)
    d.ellipse([760, 60, 1260, 560], fill=suave)
    z = zorro(principal)
    if z:
        z = _ajustar(z, 430, 560)
        img.paste(z, (W - z.width - 40, H - z.height - 20), z)
    m = 60
    d.text((m, 54), 'MI PERFIL VOCACIONAL · USB MEDELLÍN', font=texto(24, 700), fill=claro)
    _texto_ajustado(d, (m, 90), principal, titulo, 110, 640, claro)
    d.text((m, 222), f'Código {codigo_riasec}' + (f' · Secundario: {secundario}' if secundario else ''),
           font=texto(28, 600), fill=claro)
    d.rounded_rectangle([m - 12, 280, 700, H - 40], radius=26, fill=PAPEL)
    _barras(d, m + 12, 300, 600, porcentajes, texto(20, 600), texto(20, 700), 42, 10, TINTA, '#ecebf0')
    return img


def png(codigo_riasec, porcentajes, formato='historia', nombre=None, sitio=''):
    if formato == 'enlace':
        img = dibujar_enlace(codigo_riasec, porcentajes, sitio)
    else:
        img = dibujar_historia(codigo_riasec, porcentajes, nombre, sitio)
    salida = io.BytesIO()
    img.save(salida, 'PNG', optimize=True)
    return salida.getvalue()
