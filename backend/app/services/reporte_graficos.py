"""Dibujos del informe PDF: cuadros de puntaje (Competencias) y luz (Intereses)."""

from reportlab.lib import colors
from reportlab.platypus import Flowable

# La misma paleta por área de la página de resultados.
COLOR_AREA = {
    'Realista': '#eb6834', 'Investigador': '#2a78d6', 'Artístico': '#e87ba4',
    'Social': '#1baf7a', 'Emprendedor': '#eda100', 'Convencional': '#4a3aa7',
}
GRIS_AREA = '#9a9fa9'
GRIS_VACIO = '#d0cdd6'


def color_area(area):
    return colors.HexColor(COLOR_AREA.get(area, GRIS_AREA))


class Cuadros(Flowable):
    """Fila de `maximo` cuadros; se rellenan tantos como puntos valió la respuesta."""

    LADO = 9
    SEP = 3

    def __init__(self, valor, maximo, area):
        super().__init__()
        self.maximo = maximo
        self.valor = max(0, min(int(valor), maximo))
        self.color = color_area(area)
        self.width = maximo * self.LADO + (maximo - 1) * self.SEP
        self.height = self.LADO

    def wrap(self, *args):
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setLineWidth(0.8)
        for i in range(self.maximo):
            x = i * (self.LADO + self.SEP)
            if i < self.valor:
                c.setFillColor(self.color)
                c.setStrokeColor(self.color)
                c.roundRect(x, 0, self.LADO, self.LADO, 1.5, stroke=1, fill=1)
            else:
                c.setStrokeColor(colors.HexColor(GRIS_VACIO))
                c.roundRect(x, 0, self.LADO, self.LADO, 1.5, stroke=1, fill=0)


class Luz(Flowable):
    """Luz minimalista: encendida (con halo suave) o apagada (solo el contorno)."""

    RADIO = 4.5

    def __init__(self, encendida, area):
        super().__init__()
        self.encendida = bool(encendida)
        self.color = color_area(area)
        self.width = self.height = self.RADIO * 2 + 5

    def wrap(self, *args):
        return self.width, self.height

    def draw(self):
        c = self.canv
        cx = cy = self.width / 2
        c.saveState()
        if self.encendida:
            c.setFillColor(self.color)
            c.setFillAlpha(0.22)
            c.circle(cx, cy, self.RADIO + 2.2, stroke=0, fill=1)
            c.setFillAlpha(1)
            c.circle(cx, cy, self.RADIO, stroke=0, fill=1)
        else:
            c.setStrokeColor(colors.HexColor(GRIS_VACIO))
            c.setLineWidth(0.9)
            c.circle(cx, cy, self.RADIO, stroke=1, fill=0)
        c.restoreState()


# Tonos por área para fondos y textos (los mismos de la página de resultados):
# (color principal, texto oscuro legible, fondo claro)
TONOS_AREA = {
    'Realista': ('#eb6834', '#b4441a', '#fbe3d9'),
    'Investigador': ('#2a78d6', '#1c5cab', '#dbe8f8'),
    'Artístico': ('#e87ba4', '#a83d6a', '#fbe5ee'),
    'Social': ('#1baf7a', '#0b7552', '#d6f1e6'),
    'Emprendedor': ('#eda100', '#855900', '#fbedcc'),
    'Convencional': ('#4a3aa7', '#4a3aa7', '#e2dff4'),
}
TONO_NEUTRO = ('#9a9fa9', '#52514e', '#f1f0f4')


class BarrasAreas(Flowable):
    """Una barra por campo: nombre, porcentaje combinado y, debajo, el detalle
    de intereses y competencias. `filas` = [(área, combinado, intereses, competencias)]."""

    ALTO_FILA = 30
    ANCHO_NOMBRE = 92
    ANCHO_PCT = 34

    def __init__(self, filas, ancho):
        super().__init__()
        self.filas = list(filas)
        self.width = ancho
        self.height = self.ALTO_FILA * len(self.filas)

    def wrap(self, *args):
        return self.width, self.height

    def draw(self):
        c = self.canv
        largo = self.width - self.ANCHO_NOMBRE - self.ANCHO_PCT - 8
        for i, (area, combinado, intereses, competencias) in enumerate(self.filas):
            color, oscuro, claro = TONOS_AREA.get(area, TONO_NEUTRO)
            y = self.height - (i + 1) * self.ALTO_FILA + 12
            c.setFillColor(colors.HexColor(oscuro))
            c.setFont('Helvetica-Bold', 9)
            c.drawString(0, y + 1, area)
            x0 = self.ANCHO_NOMBRE
            c.setFillColor(colors.HexColor(claro))
            c.roundRect(x0, y, largo, 7, 3.5, stroke=0, fill=1)
            relleno = max(0, min(combinado, 100)) / 100 * largo
            if relleno:
                c.setFillColor(colors.HexColor(color))
                c.roundRect(x0, y, max(relleno, 7), 7, 3.5, stroke=0, fill=1)
            c.setFillColor(colors.HexColor('#1c1b22'))
            c.setFont('Helvetica-Bold', 9.5)
            c.drawRightString(self.width, y, f'{combinado}%')
            detalle = []
            if intereses is not None:
                detalle.append(f'Intereses {intereses}%')
            if competencias is not None:
                detalle.append(f'Competencias {competencias}%')
            if detalle:
                c.setFillColor(colors.HexColor('#8a8696'))
                c.setFont('Helvetica', 7)
                c.drawString(x0, y - 9.5, ' · '.join(detalle))
