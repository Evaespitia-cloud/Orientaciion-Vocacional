"""La carta para compartir: firma del enlace y dibujo de los dos formatos."""

import io

import pytest
from PIL import Image

from app import create_app
from app.services import tarjeta_service as ts

PCT = {'Realista': 63, 'Investigador': 52, 'Artístico': 63, 'Social': 60, 'Emprendedor': 43, 'Convencional': 63}


@pytest.fixture()
def contexto():
    app = create_app('development')
    with app.app_context():
        yield


def test_el_enlace_firmado_se_lee_igual(contexto):
    codigo = ts.crear_codigo('RCI', PCT)
    assert codigo.startswith('RCI-63-52-63-60-43-63.')
    assert ts.leer_codigo(codigo) == ('RCI', PCT)
    assert ts.perfiles_de('RCI') == ('Realista', 'Convencional')


@pytest.mark.parametrize('cambio', [
    lambda c: c.replace('-63', '-99', 1),      # porcentaje inventado
    lambda c: 'S' + c[1:],                     # perfil cambiado
    lambda c: c[:-2] + 'xx',                   # firma rota
    lambda c: c.split('.')[0],                 # sin firma
])
def test_un_enlace_alterado_se_rechaza(contexto, cambio):
    assert ts.leer_codigo(cambio(ts.crear_codigo('RCI', PCT))) is None


def test_dibuja_los_dos_formatos(contexto):
    historia = Image.open(io.BytesIO(ts.png('ESA', PCT, 'historia', nombre='Ana')))
    enlace = Image.open(io.BytesIO(ts.png('ESA', PCT, 'enlace')))
    assert historia.size == (1080, 1920)
    assert enlace.size == (1200, 630)
