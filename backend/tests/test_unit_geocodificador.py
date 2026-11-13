"""Pruebas del geocodificador con un índice pequeño armado en la prueba."""

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.geo import geocodificador as g  # noqa: E402

ESQUEMA = """
CREATE TABLE direcciones (municipio TEXT, via TEXT, n1 INTEGER, l1 TEXT, bis1 INTEGER, s1 INTEGER,
  n2 INTEGER, l2 TEXT, bis2 INTEGER, s2 INTEGER, placa INTEGER, lat REAL, lon REAL, estrato INTEGER,
  medidores INTEGER, celda TEXT);
"""


def fila(mpio, via, n1, l1, s1, n2, l2, s2, placa, lat, lon, estrato):
    return (mpio, via, n1, l1, 0, int(s1), n2, l2, 0, int(s2), placa, lat, lon, estrato, 1,
            f'{round(lat * 1000)}:{round(lon * 1000)}')


@pytest.fixture
def indice(tmp_path):
    ruta = tmp_path / 'indice.sqlite'
    con = sqlite3.connect(ruta)
    con.executescript(ESQUEMA)
    con.executemany('INSERT INTO direcciones VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', [
        fila('MEDELLIN', 'CL', 42, 'A', False, 108, '', False, 20, 6.2500, -75.6000, 2),
        fila('MEDELLIN', 'CL', 42, 'A', False, 108, '', False, 36, 6.2510, -75.6010, 2),
        fila('MEDELLIN', 'CL', 42, 'A', False, 108, '', False, 60, 6.2530, -75.6030, 3),
        fila('ENVIGADO', 'CR', 43, '', False, 33, 'B', True, 43, 6.1726, -75.5863, 4),
        fila('MEDELLIN', 'CL', 10, '', True, 43, '', False, 21, 6.2050, -75.5700, 5),
    ])
    con.commit()
    con.close()
    return str(ruta)


def test_coincidencia_exacta(indice):
    r = g.geocodificar('Calle 42A # 108-36', 'Medellín', ruta=indice, usar_osm=False)
    assert r['encontrada'] and r['precision'] == 'exacta'
    assert (r['lat'], r['lon'], r['estrato']) == (6.2510, -75.6010, 2)


def test_interpola_entre_placas_vecinas(indice):
    r = g.geocodificar('Calle 42A # 108-48', 'Medellín', ruta=indice, usar_osm=False)
    assert r['precision'] == 'interpolada'
    assert r['lat'] == pytest.approx(6.2520)
    assert r['lon'] == pytest.approx(-75.6020)


def test_placa_por_fuera_usa_la_mas_cercana(indice):
    r = g.geocodificar('Calle 42A # 108-70', 'Medellín', ruta=indice, usar_osm=False)
    assert r['precision'] == 'cuadra' and r['lat'] == 6.2530


def test_sur_al_final_prueba_la_via_principal(indice):
    r = g.geocodificar('Calle 10 # 43-21 sur', 'Medellín', ruta=indice, usar_osm=False)
    assert r['precision'] == 'exacta' and r['estrato'] == 5


def test_respeta_el_municipio(indice):
    r = g.geocodificar('Calle 42A # 108-36', 'Envigado', ruta=indice, usar_osm=False)
    assert not r['encontrada'] and r['motivo'] == 'sin_resultado'
    assert r['centro'] == g.CENTROS_MUNICIPIO['ENVIGADO']


def test_formato_y_municipio_invalidos(indice):
    assert g.geocodificar('mi casa', 'Medellín', ruta=indice, usar_osm=False)['motivo'] == 'formato'
    assert g.geocodificar('Calle 42A # 108-36', 'Rionegro', ruta=indice, usar_osm=False)['motivo'] == 'municipio'


def test_estrato_del_pin(indice):
    assert g.estrato_cercano(6.25101, -75.60101, ruta=indice) == 2
    assert g.estrato_cercano(6.30, -75.70, ruta=indice) is None


def test_distancia():
    # Un milésimo de grado de latitud son unos 111 m.
    assert g.distancia_m(6.25, -75.6, 6.251, -75.6) == pytest.approx(111.2, abs=0.5)
