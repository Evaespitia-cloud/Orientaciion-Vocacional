"""Estadística avanzada y mapa: solo para el panel de administración."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from ..services import analitica
from ..utils.decorators import roles_requeridos

analitica_bp = Blueprint('analitica', __name__)
ROLES = ('bienestar', 'ti', 'directivo', 'investigador')


def _simulados():
    return request.args.get('simulados') in ('1', 'true', 'si')


@analitica_bp.route('/estadistica-avanzada', methods=['GET'])
@jwt_required()
@roles_requeridos(*ROLES)
def estadistica_avanzada():
    return jsonify(analitica.estadistica_avanzada(_simulados())), 200


@analitica_bp.route('/mapa', methods=['GET'])
@jwt_required()
@roles_requeridos(*ROLES)
def mapa():
    return jsonify(analitica.mapa(_simulados())), 200
