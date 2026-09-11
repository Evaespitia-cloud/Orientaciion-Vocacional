"""Controlador de procesamiento psicométrico — cálculo de resultados y generación de perfil."""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..services.psicometrico_service import PsicometricoService
from ..models.aplicacion import Aplicacion
from ..utils.decorators import roles_requeridos

procesamiento_bp = Blueprint('procesamiento', __name__)


@procesamiento_bp.route('/calcular/<int:aplicacion_id>', methods=['POST'])
@jwt_required()
def calcular_resultados(aplicacion_id):
    """Calcular puntajes y generar perfil vocacional."""
    usuario_id = int(get_jwt_identity())
    aplicacion = Aplicacion.query.get_or_404(aplicacion_id)

    # Verificar que la aplicación esté completada
    if aplicacion.estado != 'completada':
        return jsonify({'error': 'La aplicación debe estar completada para calcular resultados'}), 400

    # Verificar permisos (propio o rol administrativo)
    from ..models.usuario import Usuario
    usuario = Usuario.query.get(usuario_id)
    if aplicacion.usuario_id != usuario_id and usuario.rol.nombre not in ('bienestar', 'ti'):
        return jsonify({'error': 'No autorizado'}), 403

    try:
        # Calcular puntajes por dimensión
        resultados = PsicometricoService.calcular_puntajes_dimension(aplicacion_id)

        # Generar perfil vocacional
        perfil = PsicometricoService.generar_perfil(aplicacion_id)

        return jsonify({
            'message': 'Resultados calculados y perfil generado',
            'resultados_dimension': [r.to_dict() for r in resultados],
            'perfil': perfil.to_dict(),
        }), 200
    except Exception as e:
        return jsonify({'error': f'Error al procesar: {str(e)}'}), 500


@procesamiento_bp.route('/puntajes-escala/<int:aplicacion_id>', methods=['GET'])
@jwt_required()
def puntajes_por_escala(aplicacion_id):
    """Obtener puntajes desglosados por escala."""
    usuario_id = int(get_jwt_identity())
    aplicacion = Aplicacion.query.get_or_404(aplicacion_id)

    from ..models.usuario import Usuario
    usuario = Usuario.query.get(usuario_id)
    if aplicacion.usuario_id != usuario_id and usuario.rol.nombre not in ('bienestar', 'ti', 'directivo'):
        return jsonify({'error': 'No autorizado'}), 403

    puntajes = PsicometricoService.calcular_puntajes_escala(aplicacion_id)
    return jsonify({'puntajes_escala': puntajes}), 200
