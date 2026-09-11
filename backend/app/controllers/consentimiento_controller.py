"""Controlador de consentimiento y confidencialidad."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from ..extensions import db
from ..models.usuario import Consentimiento

consentimiento_bp = Blueprint('consentimiento', __name__)

TEXTO_POLITICA_DEFAULT = """
POLÍTICA DE TRATAMIENTO DE DATOS PERSONALES

De conformidad con la Ley 1581 de 2012 y el Decreto 1377 de 2013, la institución
educativa informa que los datos personales recolectados a través de esta plataforma
de orientación vocacional serán tratados con las siguientes finalidades:

1. Realizar la evaluación de orientación vocacional para bachilleres.
2. Generar informes individuales y estadísticos.
3. Apoyar procesos de bienestar y orientación escolar.
4. Realizar investigación institucional con datos anonimizados.

Los datos serán custodiados con medidas de seguridad adecuadas y no serán
compartidos con terceros sin autorización previa.

El titular tiene derecho a conocer, actualizar, rectificar y suprimir sus datos
personales, así como a revocar la autorización otorgada.
"""


@consentimiento_bp.route('/', methods=['POST'])
@jwt_required()
def registrar_consentimiento():
    """Registrar aceptación/rechazo del consentimiento."""
    usuario_id = int(get_jwt_identity())
    datos = request.get_json()

    consentimiento = Consentimiento(
        usuario_id=usuario_id,
        version_politica=datos.get('version', '1.0'),
        texto_politica=datos.get('texto_politica', TEXTO_POLITICA_DEFAULT),
        aceptado=datos.get('aceptado', False),
        ip_address=request.remote_addr,
        fecha_aceptacion=datetime.utcnow() if datos.get('aceptado') else None,
    )

    db.session.add(consentimiento)
    db.session.commit()

    return jsonify({
        'message': 'Consentimiento registrado',
        'consentimiento': consentimiento.to_dict()
    }), 201


@consentimiento_bp.route('/estado', methods=['GET'])
@jwt_required()
def estado_consentimiento():
    """Verificar si el usuario tiene consentimiento vigente."""
    usuario_id = int(get_jwt_identity())
    consentimiento = Consentimiento.query.filter_by(
        usuario_id=usuario_id, aceptado=True
    ).order_by(Consentimiento.created_at.desc()).first()

    return jsonify({
        'tiene_consentimiento': consentimiento is not None,
        'consentimiento': consentimiento.to_dict() if consentimiento else None,
        'texto_politica': TEXTO_POLITICA_DEFAULT,
    }), 200
