"""Controlador escolar: municipios y buscador de colegios (los usa el registro)."""
from flask import Blueprint, jsonify, request
from ..services import escolar_service
from ..services.geo.direcciones import MUNICIPIOS
from ..utils.rate_limit import allow_request, ip_cliente

escolar_bp = Blueprint('escolar', __name__)
# Sin texto escrito la lista se despliega completa, así que caben más resultados.
LIMITE_BUSQUEDA, LIMITE_LISTA = 12, 60


@escolar_bp.route('/municipios', methods=['GET'])
def municipios():
    """Los diez municipios del Valle de Aburrá (público: lo usa el registro)."""
    return jsonify({'municipios': [{'clave': m, 'nombre': m.title().replace('Itagui', 'Itagüí')
                                    .replace('Medellin', 'Medellín')} for m in MUNICIPIOS]}), 200


@escolar_bp.route('/colegios', methods=['GET'])
def colegios():
    """Lista de colegios por sector y autocompletar (público: el catálogo es información abierta).

    Parámetros: ``q`` (texto), ``sector`` (público/oficial o privado) y ``municipio``.
    Con sector y sin texto devuelve la lista para desplegar en el registro.
    """
    if not allow_request(f'colegios:{ip_cliente()}', 120, 60):
        return jsonify({'error': 'Demasiadas búsquedas seguidas.'}), 429
    consulta = (request.args.get('q') or '')[:80]
    sector = request.args.get('sector')
    municipio = request.args.get('municipio')
    limite = LIMITE_BUSQUEDA if consulta.strip() else LIMITE_LISTA
    hallados = escolar_service.buscar_colegios(consulta, municipio, sector, limite)
    # El total solo tiene sentido cuando la lista no está filtrada por texto.
    total = len(hallados) if consulta.strip() else escolar_service.contar_colegios(sector, municipio)
    return jsonify({'colegios': hallados, 'limite': limite, 'total': total}), 200
