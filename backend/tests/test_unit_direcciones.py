"""Pruebas del normalizador de direcciones (formato de nomenclatura del Valle de Aburrá)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.geo.direcciones import normalizar, municipio_canonico  # noqa: E402


def clave(texto):
    d = normalizar(texto)
    return None if d is None else (d.via, d.n1, d.l1, d.bis1, d.s1, d.n2, d.l2, d.bis2, d.s2, d.placa)


@pytest.mark.parametrize('texto, esperado', [
    # Formato de EPM
    ('CL 42 A CR 108 -36', ('CL', 42, 'A', False, False, 108, '', False, False, 36)),
    ('CR 40 CL 71 SUR -15', ('CR', 40, '', False, False, 71, '', False, True, 15)),
    ('CL 17 C SUR CR 44 -117', ('CL', 17, 'C', False, True, 44, '', False, False, 117)),
    ('DIAG 31 BB TRAN 32 CC SUR -10', ('DIAG', 31, 'BB', False, False, 32, 'CC', False, True, 10)),
    ('CR 24 DA CL 10 E -205', ('CR', 24, 'DA', False, False, 10, 'E', False, False, 205)),
    # Como lo escribe una persona
    ('Calle 42A # 108-36', ('CL', 42, 'A', False, False, 108, '', False, False, 36)),
    ('cra. 43 nro. 33 b sur 43', ('CR', 43, '', False, False, 33, 'B', False, True, 43)),
    ('Carrera 80 C N° 33 - 32 apto 301', ('CR', 80, 'C', False, False, 33, '', False, False, 32)),
    ('Diagonal 85A # 38 sur-27', ('DIAG', 85, 'A', False, False, 38, '', False, True, 27)),
    ('Transversal 32CC #31BB-10', ('TRAN', 32, 'CC', False, False, 31, 'BB', False, False, 10)),
    ('IND CRA 44 NO.38 SUR 15', ('CR', 44, '', False, False, 38, '', False, True, 15)),
    ('Calle 10 # 43-21 sur', ('CL', 10, '', False, False, 43, '', False, True, 21)),
    ('Cl 50 bis # 45-30', ('CL', 50, '', True, False, 45, '', False, False, 30)),
    ('Avenida 80 # 33-32', ('AVDA', 80, '', False, False, 33, '', False, False, 32)),
    ('Circular 1 # 70-1', ('CIRC', 1, '', False, False, 70, '', False, False, 1)),
    # "S" como abreviatura de SUR, puntos pegados y codificación rota
    ('CRA. 40 Nro. 38 A S 08', ('CR', 40, '', False, False, 38, 'A', False, True, 8)),
    ('CL. 39 B S 30 16', ('CL', 39, 'B', False, True, 30, '', False, False, 16)),
    ('CRA 47 NRO 27S-94', ('CR', 47, '', False, False, 27, '', False, True, 94)),
    ('CRA.43A NO.31A SUR 41', ('CR', 43, 'A', False, False, 31, 'A', False, True, 41)),
    ('CALLE 45 B sur N� 42 C � 9', ('CL', 45, 'B', False, True, 42, 'C', False, False, 9)),
    ('Transv. 35 C Sur 33 70', ('TRAN', 35, 'C', False, True, 33, '', False, False, 70)),
])
def test_normaliza_direcciones(texto, esperado):
    assert clave(texto) == esperado


@pytest.mark.parametrize('texto', ['', 'Vereda El Pinar', 'RURAL_177000450900000000_GIRARDOTA', 'Calle 42A', None])
def test_rechaza_lo_que_no_es_direccion_urbana(texto):
    assert normalizar(texto) is None


def test_complemento_y_texto_normalizado():
    d = normalizar('Carrera 80 C N° 33 - 32 apto 301')
    assert d.complemento == 'APTO 301'
    assert d.texto() == 'CR 80 C # 33 - 32'


@pytest.mark.parametrize('nombre, canonico', [
    ('Medellín', 'MEDELLIN'), ('Itagüí', 'ITAGUI'), ('la estrella', 'LA ESTRELLA'), ('BELLO', 'BELLO'),
])
def test_municipio_canonico(nombre, canonico):
    assert municipio_canonico(nombre) == canonico
