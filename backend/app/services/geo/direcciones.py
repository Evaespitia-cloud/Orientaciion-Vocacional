"""Normalización de direcciones con la nomenclatura del Valle de Aburrá.

Lleva una dirección escrita a mano ("Calle 42A # 108-36") y una del catastro de
EPM ("CL 42 A CR 108 -36") a la misma estructura: vía principal, número,
letras, BIS y SUR, número del cruce con sus letras, BIS y SUR, y la placa.
Con esa estructura las dos se pueden comparar campo por campo.

El tipo de vía del cruce no se guarda: quien escribe "#" no dice si cruza una
calle o una carrera, y en el catastro casi siempre es la contraria.
"""

import re
import unicodedata
from dataclasses import dataclass

VIAS = {
    'CL': 'CL', 'CLL': 'CL', 'CALL': 'CL', 'CALLE': 'CL', 'CAL': 'CL',
    'CR': 'CR', 'CRA': 'CR', 'KR': 'CR', 'KRA': 'CR', 'CARRERA': 'CR', 'CARERA': 'CR', 'CRR': 'CR', 'CAR': 'CR',
    'DG': 'DIAG', 'DIAG': 'DIAG', 'DIAGONAL': 'DIAG',
    'TV': 'TRAN', 'TR': 'TRAN', 'TRV': 'TRAN', 'TRANS': 'TRAN', 'TRAN': 'TRAN', 'TRANSVERSAL': 'TRAN',
    'TRANSV': 'TRAN', 'TRASV': 'TRAN', 'TRASVERSAL': 'TRAN',
    'CIR': 'CIRC', 'CIRC': 'CIRC', 'CIRCULAR': 'CIRC',
    'AV': 'AVDA', 'AVDA': 'AVDA', 'AVENIDA': 'AVDA',
}

MUNICIPIOS = ('MEDELLIN', 'BELLO', 'ITAGUI', 'ENVIGADO', 'SABANETA', 'CALDAS',
              'COPACABANA', 'LA ESTRELLA', 'BARBOSA', 'GIRARDOTA')

# Palabras que separan la vía principal del cruce.
_NUMERAL = r'(?:#|N[O°º]?\.?|NRO\.?|NUM\.?|NUMERO)'
# Lo que viene después de la placa y no hace parte de la dirección.
_COMPLEMENTO = re.compile(r'\b(APTO|APARTAMENTO|AP|INT|INTERIOR|CASA|PISO|BLOQUE|BL|TORRE|LOCAL|OF|OFICINA|ETAPA|URB)\b.*$')

_PATRON = re.compile(
    r'\b(?P<via>' + '|'.join(sorted(VIAS, key=len, reverse=True)) + r')\.?\s+'
    r'(?P<n1>\d{1,3})\s*(?P<l1>(?:[A-Z]{1,3}\s*)*?)\s*(?P<bis1>BIS)?\s*(?P<s1>SUR|ESTE)?\s*'
    r'(?:' + _NUMERAL + r'|(?:' + '|'.join(sorted(VIAS, key=len, reverse=True)) + r')\.?)?\s*'
    r'(?P<n2>\d{1,3})\s*(?P<l2>(?:[A-Z]{1,3}\s*)*?)\s*(?P<bis2>BIS)?\s*(?P<s2>SUR|ESTE)?\s*'
    r'-?\s*(?P<placa>\d{1,4})\s*(?P<s3>SUR|ESTE)?\b'
)


@dataclass(frozen=True)
class Direccion:
    via: str
    n1: int
    l1: str
    bis1: bool
    s1: bool
    n2: int
    l2: str
    bis2: bool
    s2: bool
    placa: int
    complemento: str = ''

    def clave_cuadra(self):
        """Todo menos la placa: identifica el costado de cuadra."""
        return (self.via, self.n1, self.l1, self.bis1, self.s1, self.n2, self.l2, self.bis2, self.s2)

    def texto(self):
        def parte(n, letras, bis, sur):
            return ' '.join(x for x in (str(n), letras, 'BIS' if bis else '', 'SUR' if sur else '') if x)
        return f'{self.via} {parte(self.n1, self.l1, self.bis1, self.s1)} # {parte(self.n2, self.l2, self.bis2, self.s2)} - {self.placa}'


def sin_tildes(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')


def municipio_canonico(nombre):
    if not nombre:
        return None
    limpio = re.sub(r'\s+', ' ', sin_tildes(str(nombre)).upper().strip())
    return limpio if limpio in MUNICIPIOS else None


def _preparar(texto):
    t = texto.upper()
    # Archivos con la codificación rota traen "N�" donde iba "N°" y "�" donde iba un guion.
    t = t.replace('N�', ' # ').replace('�', ' - ')
    t = t.replace('Nº', ' # ').replace('N°', ' # ').replace('NO.', ' # ').replace('NRO.', ' # ')
    t = re.sub(r'[–—]', '-', sin_tildes(t))
    t = re.sub(r'\(.*?\)', ' ', t)
    # Separa número y letra pegados: 42A -> 42 A, A21 -> A 21
    t = re.sub(r'(\d)([A-Z])', r'\1 \2', t)
    t = re.sub(r'([A-Z])(\d)', r'\1 \2', t)
    t = re.sub(r'[,;:.]', ' ', t)
    t = re.sub(r'\s*-\s*', ' - ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    # "S" suelta o pegada a la letra ("38 A S", "39 BS", "27 S") es la abreviatura de SUR.
    fichas, tras_numero = [], False
    for f in t.split(' '):
        if tras_numero and f == 'S':
            f = 'SUR'
        elif tras_numero and re.fullmatch(r'[A-Z]{1,2}S', f) and f not in ('BIS', 'SUR'):
            f = f[:-1] + ' SUR'
        if f.isdigit():
            tras_numero = True
        elif not re.fullmatch(r'[A-Z]{1,3}', f) or f in VIAS:
            tras_numero = False
        fichas.append(f)
    return ' '.join(fichas)


def _letras(grupo):
    letras = ''.join(grupo.split()) if grupo else ''
    # "SUR" y "BIS" se capturan aparte; si se colaron entre las letras, se quitan.
    return letras if letras not in ('SUR', 'BIS', 'ESTE') else ''


def normalizar(texto):
    """Devuelve la Direccion o None si el texto no es una dirección urbana con placa."""
    if not texto or not isinstance(texto, str) or texto.upper().startswith('RURAL_'):
        return None
    t = _preparar(texto)
    m = _PATRON.search(t)
    if not m:
        return None
    resto = t[m.end():].strip(' -')
    complemento = ''
    c = _COMPLEMENTO.search(resto)
    if c:
        complemento = c.group(0).strip()
    s2 = bool(m.group('s2')) or bool(m.group('s3'))
    return Direccion(
        via=VIAS[m.group('via')],
        n1=int(m.group('n1')), l1=_letras(m.group('l1')), bis1=bool(m.group('bis1')), s1=bool(m.group('s1')),
        n2=int(m.group('n2')), l2=_letras(m.group('l2')), bis2=bool(m.group('bis2')), s2=s2,
        placa=int(m.group('placa')), complemento=complemento,
    )
