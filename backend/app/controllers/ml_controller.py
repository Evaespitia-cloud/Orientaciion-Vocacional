"""
Controlador ML — endpoints para Clustering y PLN.

Rutas base: /api/ml/
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..extensions import db
from ..models.aplicacion import Aplicacion
from ..models.ml_models import ClusteringResultado, PlnAnalisis
from ..services.clustering_service import ClusteringService
from ..services.pln_service import PlnService
from ..utils.decorators import roles_requeridos
from ..utils.audit import registrar_auditoria

ml_bp = Blueprint('ml', __name__)


# ═══════════════════════════════════════════════════════════════════════════
# CLUSTERING
# ═══════════════════════════════════════════════════════════════════════════

@ml_bp.route('/clustering/combinaciones', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo', 'investigador')
def combinaciones_clustering():
    """Retorna el catálogo completo de parejas RIASEC no dirigidas."""
    return jsonify({'combinaciones': ClusteringService.catalogo_combinaciones()}), 200

@ml_bp.route('/clustering/ejecutar', methods=['POST'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo', 'investigador')
def ejecutar_clustering():
    """
    Ejecuta K-Means sobre los perfiles RIASEC de estudiantes completados.
    Body (opcional): { "configuracion_id": int, "n_clusters": int }
    """
    datos = request.get_json() or {}
    configuracion_id = datos.get('configuracion_id')
    n_clusters = datos.get('n_clusters')

    if n_clusters is not None:
        try:
            n_clusters = int(n_clusters)
            if not (2 <= n_clusters <= 10):
                return jsonify({'error': 'n_clusters debe estar entre 2 y 10'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'n_clusters debe ser un entero'}), 400

    try:
        usuario_id = int(get_jwt_identity())
        resultado = ClusteringService.ejecutar(
            configuracion_id=configuracion_id,
            n_clusters=n_clusters,
        )
        registrar_auditoria(
            usuario_id,
            'clustering_ejecutado',
            'ml',
            descripcion=f"Clustering k={resultado.get('n_clusters')} sobre {resultado.get('n_aplicaciones')} aplicaciones",
            datos_nuevos=resultado,
        )
        return jsonify({'resultado': resultado}), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 422
    except Exception as e:
        return jsonify({'error': f'Error al ejecutar clustering: {str(e)}'}), 500


@ml_bp.route('/clustering/historial', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo', 'investigador')
def historial_clustering():
    """Retorna los ultimos 10 resultados de clustering."""
    limit = request.args.get('limit', 10, type=int)
    historial = ClusteringService.historial(limit=limit)
    return jsonify({'historial': historial, 'total': len(historial)}), 200


@ml_bp.route('/clustering/<int:resultado_id>', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo', 'investigador')
def detalle_clustering(resultado_id):
    """Retorna detalle completo de un resultado de clustering con asignaciones."""
    try:
        detalle = ClusteringService.detalle(resultado_id)
        return jsonify({'detalle': detalle}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 404


@ml_bp.route('/clustering/mi-cluster', methods=['GET'])
@jwt_required()
def mi_cluster():
    """Retorna el cluster asignado al estudiante actual (ultima ejecucion)."""
    usuario_id = int(get_jwt_identity())
    resultado_id = request.args.get('resultado_id', type=int)

    aplicacion = (
        Aplicacion.query
        .filter_by(usuario_id=usuario_id, estado='completada')
        .order_by(Aplicacion.fecha_fin.desc())
        .first()
    )
    if not aplicacion:
        return jsonify({'cluster': None, 'mensaje': 'No tienes aplicaciones completadas'}), 200

    cluster = ClusteringService.cluster_del_estudiante(aplicacion.id, resultado_id)
    if not cluster:
        return jsonify({'cluster': None, 'mensaje': 'Aun no se ha ejecutado el clustering'}), 200

    resultado = ClusteringResultado.query.get(cluster['resultado_id'])
    descripcion = None
    if resultado and resultado.descripcion_clusters:
        for desc in resultado.descripcion_clusters:
            if desc.get('cluster') == cluster['cluster_id']:
                descripcion = desc
                break

    return jsonify({'cluster': cluster, 'descripcion': descripcion}), 200


# ═══════════════════════════════════════════════════════════════════════════
# PLN — PROCESAMIENTO DE LENGUAJE NATURAL
# ═══════════════════════════════════════════════════════════════════════════

@ml_bp.route('/pln/analizar-texto', methods=['POST'])
@jwt_required()
def pln_analizar_texto():
    """Analiza texto libre y retorna scores RIASEC."""
    datos = request.get_json() or {}
    texto = datos.get('texto', '')
    if not texto.strip():
        return jsonify({'error': 'El campo texto es requerido'}), 400

    resultado = PlnService.analizar_texto(texto)
    return jsonify({'analisis': resultado}), 200


@ml_bp.route('/pln/analizar-respuesta/<int:respuesta_id>', methods=['POST'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo', 'investigador')
def pln_analizar_respuesta(respuesta_id):
    """Analiza una respuesta abierta y persiste el resultado PLN."""
    try:
        resultado = PlnService.analizar_respuesta(respuesta_id)
        return jsonify({'analisis': resultado}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ml_bp.route('/pln/analizar-aplicacion/<int:aplicacion_id>', methods=['POST'])
@jwt_required()
def pln_analizar_aplicacion(aplicacion_id):
    """Analiza todas las respuestas abiertas de una aplicacion."""
    usuario_id = int(get_jwt_identity())
    aplicacion = Aplicacion.query.get_or_404(aplicacion_id)

    from ..models.usuario import Usuario
    usuario = Usuario.query.get(usuario_id)
    if aplicacion.usuario_id != usuario_id and usuario.rol.nombre not in ('bienestar', 'ti', 'directivo', 'investigador'):
        return jsonify({'error': 'No autorizado'}), 403

    resultado = PlnService.analizar_aplicacion(aplicacion_id)
    return jsonify({'pln': resultado}), 200


@ml_bp.route('/pln/resultado/<int:respuesta_id>', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo', 'investigador')
def pln_resultado_respuesta(respuesta_id):
    """Retorna el analisis PLN guardado de una respuesta especifica."""
    analisis = PlnAnalisis.query.filter_by(respuesta_id=respuesta_id).first()
    if not analisis:
        return jsonify({'analisis': None, 'mensaje': 'No hay analisis PLN para esta respuesta'}), 200
    return jsonify({'analisis': analisis.to_dict()}), 200


# ═══════════════════════════════════════════════════════════════════════════
# RESUMEN GENERAL ML
# ═══════════════════════════════════════════════════════════════════════════

@ml_bp.route('/resumen', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo', 'investigador')
def resumen_ml():
    """Retorna un resumen del estado de los modulos ML."""
    n_clustering = ClusteringResultado.query.count()
    ultimo_clustering = ClusteringResultado.query.order_by(
        ClusteringResultado.created_at.desc()
    ).first()
    n_pln_analisis = PlnAnalisis.query.count()

    return jsonify({
        'clustering': {
            'total_ejecuciones': n_clustering,
            'ultimo_resultado': ultimo_clustering.to_dict() if ultimo_clustering else None,
        },
        'pln': {
            'total_analisis': n_pln_analisis,
        },
    }), 200
