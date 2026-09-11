"""Controlador de generación y descarga de reportes PDF."""

import os
from flask import Blueprint, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..services.reporte_service import ReporteService
from ..models.resultado import PerfilVocacional, Reporte
from ..models.aplicacion import Aplicacion
from ..extensions import db

reporte_bp = Blueprint('reportes', __name__)


@reporte_bp.route('/generar/<int:aplicacion_id>', methods=['POST'])
@jwt_required()
def generar_reporte(aplicacion_id):
    """Generar reporte PDF para una aplicación."""
    usuario_id = int(get_jwt_identity())
    aplicacion = Aplicacion.query.get_or_404(aplicacion_id)

    # Verificar permisos
    from ..models.usuario import Usuario
    usuario = Usuario.query.get(usuario_id)
    if aplicacion.usuario_id != usuario_id and usuario.rol.nombre not in ('bienestar', 'ti'):
        return jsonify({'error': 'No autorizado'}), 403

    perfil = PerfilVocacional.query.filter_by(aplicacion_id=aplicacion_id).first()
    if not perfil:
        return jsonify({'error': 'No se ha generado perfil para esta aplicación. Procese los resultados primero.'}), 400

    try:
        reporte = ReporteService.generar_reporte_individual(perfil.id, generado_por=usuario_id)
        return jsonify({
            'message': 'Reporte generado exitosamente',
            'reporte': reporte.to_dict(),
        }), 201
    except Exception as e:
        return jsonify({'error': f'Error al generar reporte: {str(e)}'}), 500


@reporte_bp.route('/descargar/<int:reporte_id>', methods=['GET'])
@jwt_required()
def descargar_reporte(reporte_id):
    """Descargar un reporte PDF."""
    usuario_id = int(get_jwt_identity())
    reporte = Reporte.query.get_or_404(reporte_id)

    # Verificar permisos
    from ..models.usuario import Usuario
    usuario = Usuario.query.get(usuario_id)
    perfil = reporte.perfil
    aplicacion = perfil.aplicacion

    if aplicacion.usuario_id != usuario_id and usuario.rol.nombre not in ('bienestar', 'ti'):
        return jsonify({'error': 'No autorizado'}), 403

    if not reporte.ruta_archivo or not os.path.exists(reporte.ruta_archivo):
        return jsonify({'error': 'Archivo de reporte no encontrado'}), 404

    # Marcar como descargado
    from datetime import datetime
    reporte.descargado = True
    reporte.fecha_descarga = datetime.utcnow()
    db.session.commit()

    return send_file(
        reporte.ruta_archivo,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=os.path.basename(reporte.ruta_archivo),
    )


@reporte_bp.route('/listar', methods=['GET'])
@jwt_required()
def listar_reportes():
    """Listar reportes del usuario o todos (según rol)."""
    usuario_id = int(get_jwt_identity())
    from ..models.usuario import Usuario
    usuario = Usuario.query.get(usuario_id)

    if usuario.rol.nombre in ('bienestar', 'ti', 'directivo'):
        reportes = Reporte.query.order_by(Reporte.created_at.desc()).all()
    else:
        reportes = Reporte.query.join(PerfilVocacional).join(Aplicacion).filter(
            Aplicacion.usuario_id == usuario_id
        ).order_by(Reporte.created_at.desc()).all()

    return jsonify({'reportes': [r.to_dict() for r in reportes]}), 200
