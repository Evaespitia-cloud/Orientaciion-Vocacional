"""Límites por visitante: detrás del frontend todas las peticiones llegan desde 127.0.0.1."""

from flask import Flask

from app.utils import rate_limit
from app.utils.rate_limit import allow_request, ip_cliente

app = Flask(__name__)


def ip(remota, cabecera=None):
    entorno = {'REMOTE_ADDR': remota}
    headers = {rate_limit.CABECERA_IP: cabecera} if cabecera else {}
    with app.test_request_context('/', environ_base=entorno, headers=headers):
        return ip_cliente()


def test_desde_el_frontend_usa_la_ip_reenviada():
    assert ip('127.0.0.1', '181.50.10.7') == '181.50.10.7'


def test_sin_cabecera_usa_la_remota():
    assert ip('127.0.0.1') == '127.0.0.1'


def test_desde_afuera_ignora_la_cabecera():
    # Alguien que llegue directo al backend no puede hacerse pasar por otra IP.
    assert ip('200.1.2.3', '1.1.1.1') == '200.1.2.3'


def test_el_limite_de_registro_es_por_visitante():
    rate_limit._attempts.clear()
    for _ in range(5):
        assert allow_request(f'registro:{ip("127.0.0.1", "10.0.0.1")}', 5, 600)
    assert not allow_request(f'registro:{ip("127.0.0.1", "10.0.0.1")}', 5, 600)
    # Otro estudiante del mismo salón no queda bloqueado por el primero.
    assert allow_request(f'registro:{ip("127.0.0.1", "10.0.0.2")}', 5, 600)
