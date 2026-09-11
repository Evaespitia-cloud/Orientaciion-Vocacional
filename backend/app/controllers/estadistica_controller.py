"""Controlador de estadísticas e indicadores institucionales."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import db
from ..services.estadistica_service import EstadisticaService
from ..utils.decorators import roles_requeridos
from .aplicacion_controller import expirar_aplicaciones_abandonadas

estadistica_bp = Blueprint('estadisticas', __name__)


@estadistica_bp.route('/resumen', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo', 'investigador')
def resumen_general():
    """Obtener resumen general del sistema. Dispara barrido global de pruebas expiradas."""
    expirar_aplicaciones_abandonadas()  # barrido global de todas las pruebas vencidas
    return jsonify(EstadisticaService.resumen_general()), 200


@estadistica_bp.route('/participacion', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo', 'investigador')
def participacion():
    """Estadísticas de participación."""
    config_id = request.args.get('configuracion_id', type=int)
    return jsonify(EstadisticaService.estadisticas_participacion(config_id)), 200


@estadistica_bp.route('/perfiles', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo', 'investigador')
def distribucion_perfiles():
    """Distribución de perfiles vocacionales."""
    config_id = request.args.get('configuracion_id', type=int)
    return jsonify({
        'distribucion': EstadisticaService.distribucion_perfiles(config_id)
    }), 200


@estadistica_bp.route('/por-grado', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo')
def por_grado():
    """Estadísticas por grado escolar."""
    config_id = request.args.get('configuracion_id', type=int)
    return jsonify({
        'grados': EstadisticaService.estadisticas_por_grado(config_id)
    }), 200


@estadistica_bp.route('/por-institucion', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo', 'investigador')
def por_institucion():
    """Estadísticas por institución educativa."""
    config_id = request.args.get('configuracion_id', type=int)
    return jsonify({
        'instituciones': EstadisticaService.estadisticas_por_institucion(config_id)
    }), 200


@estadistica_bp.route('/dimensiones', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo', 'investigador')
def promedios_dimensiones():
    """Promedios de puntajes por dimensión."""
    config_id = request.args.get('configuracion_id', type=int)
    return jsonify({
        'dimensiones': EstadisticaService.promedios_dimensiones(config_id)
    }), 200


@estadistica_bp.route('/por-tipo-colegio', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo', 'investigador')
def por_tipo_colegio():
    """Estadísticas comparativas por tipo de colegio (público/privado)."""
    return jsonify({
        'tipo_colegio': EstadisticaService.estadisticas_por_tipo_colegio()
    }), 200


@estadistica_bp.route('/por-instrumento', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo', 'investigador')
def por_instrumento():
    """Participación y porcentajes desglosados por instrumento/configuración."""
    return jsonify({
        'instrumentos': EstadisticaService.participacion_por_instrumento()
    }), 200


@estadistica_bp.route('/perfiles-por-instrumento', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo', 'investigador')
def perfiles_por_instrumento():
    """Distribución de perfiles vocacionales por instrumento."""
    return jsonify({
        'instrumentos': EstadisticaService.distribucion_perfiles_por_instrumento()
    }), 200


@estadistica_bp.route('/perfiles-por-colegio', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo', 'investigador')
def perfiles_por_colegio():
    """Distribución de perfiles Holland por tipo de colegio."""
    return jsonify({
        'distribucion': EstadisticaService.distribucion_perfiles_por_tipo_colegio()
    }), 200


@estadistica_bp.route('/areas-interes', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo', 'investigador')
def areas_interes():
    """Distribución general por áreas de interés Holland."""
    return jsonify({
        'distribucion': EstadisticaService.distribucion_por_areas_interes()
    }), 200


# ─── Evolución vocacional del estudiante ─────────────────────────────────── #

@estadistica_bp.route('/evolucion/mi-evolucion', methods=['GET'])
@jwt_required()
def mi_evolucion():
    """Historial de evolución vocacional del estudiante autenticado."""
    identidad = get_jwt_identity()
    usuario_id = int(identidad.get('id') if isinstance(identidad, dict) else identidad)
    hasta_aplicacion_id = request.args.get('hasta_aplicacion_id', type=int)

    evolucion = EstadisticaService.evolucion_estudiante(usuario_id, hasta_aplicacion_id=hasta_aplicacion_id)
    mutaciones = EstadisticaService.mutaciones_vocacionales(usuario_id, hasta_aplicacion_id=hasta_aplicacion_id)
    prediccion = EstadisticaService.prediccion_vocacional(usuario_id, hasta_aplicacion_id=hasta_aplicacion_id)

    return jsonify({
        'evolucion': evolucion,
        'mutaciones': mutaciones,
        'prediccion': prediccion,
    }), 200


@estadistica_bp.route('/evolucion/<int:usuario_id>', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo', 'investigador')
def evolucion_estudiante(usuario_id):
    """Historial de evolución vocacional para un estudiante específico (admin)."""
    hasta_aplicacion_id = request.args.get('hasta_aplicacion_id', type=int)
    evolucion = EstadisticaService.evolucion_estudiante(usuario_id, hasta_aplicacion_id=hasta_aplicacion_id)
    mutaciones = EstadisticaService.mutaciones_vocacionales(usuario_id, hasta_aplicacion_id=hasta_aplicacion_id)
    prediccion = EstadisticaService.prediccion_vocacional(usuario_id, hasta_aplicacion_id=hasta_aplicacion_id)

    return jsonify({
        'evolucion': evolucion,
        'mutaciones': mutaciones,
        'prediccion': prediccion,
    }), 200



@estadistica_bp.route('/evolucion-agregada', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo', 'investigador')
def evolucion_agregada():
    """Distribución de perfiles Holland mes a mes para toda la institución."""
    # Determinar el rol del usuario
    rol = None
    try:
        from flask_jwt_extended import get_jwt
        claims = get_jwt()
        rol = claims.get('rol')
    except Exception:
        pass

    if rol == 'investigador':
        return jsonify({'mensaje': 'Acceso denegado'}), 403
    elif rol in ['bienestar', 'ti', 'directivo']:
        # Evolución vocacional institucional (gráfica de líneas por mes y perfil)
        from sqlalchemy import extract
        from ..models.resultado import PerfilVocacional
        from ..models.aplicacion import Aplicacion
        resultados = (
            db.session.query(
                extract('year', Aplicacion.fecha_fin).label('anio'),
                extract('month', Aplicacion.fecha_fin).label('mes'),
                PerfilVocacional.perfil_principal,
                db.func.count(PerfilVocacional.id).label('cantidad'),
            )
            .join(Aplicacion, PerfilVocacional.aplicacion_id == Aplicacion.id)
            .filter(Aplicacion.estado == 'completada')
            .group_by('anio', 'mes', PerfilVocacional.perfil_principal)
            .order_by('anio', 'mes')
            .all()
        )
        periodos = {}
        for r in resultados:
            key = f"{int(r.anio)}-{int(r.mes):02d}"
            if key not in periodos:
                periodos[key] = {'periodo': key, 'perfiles': {}}
            periodos[key]['perfiles'][r.perfil_principal] = r.cantidad
        return jsonify({'evolucion': list(periodos.values())}), 200
    else:
        return jsonify({'mensaje': 'Acceso denegado'}), 403


# ─── Segmentación demográfica ─────────────────────────────────────────────── #

@estadistica_bp.route('/segmentacion/genero', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo', 'investigador')
def segmentacion_genero():
    """Distribución de perfiles segmentada por género."""
    return jsonify({
        'segmentacion': EstadisticaService.segmentacion_genero(),
        'conteo': EstadisticaService.conteo_por_genero(),
    }), 200


@estadistica_bp.route('/segmentacion/edad', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo', 'investigador')
def segmentacion_edad():
    """Distribución de perfiles segmentada por rango de edad."""
    return jsonify({
        'segmentacion': EstadisticaService.segmentacion_edad(),
        'conteo': EstadisticaService.conteo_por_edad(),
    }), 200


@estadistica_bp.route('/resumen-estudiantes', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo', 'investigador')
def resumen_estudiantes():
    """Lista de todos los estudiantes con conteo de pruebas y último perfil."""
    buscar   = request.args.get('buscar', '').strip()
    page     = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    resultado = EstadisticaService.resumen_evolucion_estudiantes(
        buscar=buscar, page=page, per_page=per_page
    )
    return jsonify(resultado), 200
