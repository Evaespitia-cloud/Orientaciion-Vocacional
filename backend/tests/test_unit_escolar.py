"""Perfil escolar desde el registro: colegio, edad y dirección ubicada en el servidor."""

import sqlite3

import pytest

from app import create_app
from app.extensions import db as _db
from app.models.escolar import SedeEducativa
from app.models.usuario import Rol, Usuario
from app.services import escolar_service

ESQUEMA = """
CREATE TABLE direcciones (municipio TEXT, via TEXT, n1 INTEGER, l1 TEXT, bis1 INTEGER, s1 INTEGER,
  n2 INTEGER, l2 TEXT, bis2 INTEGER, s2 INTEGER, placa INTEGER, lat REAL, lon REAL, estrato INTEGER,
  medidores INTEGER, celda TEXT);
INSERT INTO direcciones VALUES ('BELLO','AVDA',43,'',0,0,59,'',0,0,4,6.3320,-75.5560,3,1,'6332:-75556');
"""


@pytest.fixture()
def app(tmp_path, monkeypatch):
    indice = tmp_path / 'indice.sqlite'
    con = sqlite3.connect(indice)
    con.executescript(ESQUEMA)
    con.close()
    monkeypatch.setenv('INDICE_DIRECCIONES', str(indice))
    monkeypatch.setenv('GEOCODIFICAR_OSM', '0')
    app = create_app('development')
    with app.app_context():
        assert ':memory:' in str(_db.engine.url)
        _db.create_all()
        rol = Rol(nombre='estudiante')
        _db.session.add(rol)
        _db.session.flush()
        _db.session.add(Usuario(email='e@x.co', password_hash='x', nombres='E', apellidos='X', rol_id=rol.id))
        _db.session.add(SedeEducativa(codigo='105088000001', nombre='IE Concejo de Bello', sector='Oficial',
                                      municipio='BELLO', lat=6.33, lon=-75.55))
        _db.session.commit()
        yield app
        _db.session.remove()
        _db.drop_all()


def usuario_id():
    return Usuario.query.filter_by(email='e@x.co').one().id


def test_direccion_encontrada_se_ubica_sola(app):
    p = escolar_service.guardar_perfil(usuario_id(), {
        'sede_codigo': '105088000001', 'edad': '16', 'municipio': 'BELLO', 'direccion': 'avenida 43 # 59-4'})
    assert (p.sector, p.edad, p.municipio) == ('Oficial', 16, 'BELLO')
    assert (p.lat, p.lon, p.precision, p.estrato) == (6.332, -75.556, 'exacta', 3)


def test_direccion_no_encontrada_queda_solo_el_texto(app):
    p = escolar_service.guardar_perfil(usuario_id(), {'municipio': 'BELLO', 'direccion': 'Calle 99 # 1-1'})
    assert p.direccion == 'Calle 99 # 1-1'
    assert p.lat is None and p.precision is None


def test_colegio_escrito_a_mano_sin_sector(app):
    p = escolar_service.guardar_perfil(usuario_id(), {'colegio_texto': 'Colegio Nuevo del Norte'})
    assert (p.sede_codigo, p.colegio_texto, p.sector) == (None, 'Colegio Nuevo del Norte', None)


@pytest.mark.parametrize('datos, mensaje', [
    ({'edad': '40'}, 'entre 12 y 25'),
    ({'edad': 'diez'}, 'número'),
    ({'sede_codigo': 'no-existe'}, 'catálogo'),
    ({'direccion': 'Calle 1 # 2-3'}, 'municipio'),
])
def test_validacion(app, datos, mensaje):
    with pytest.raises(ValueError, match=mensaje):
        escolar_service.validar(datos)
