"""Controlador de aplicación del instrumento — iniciar, continuar, guardar respuestas."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from sqlalchemy import func
from ..extensions import db
from ..models.aplicacion import Aplicacion, Respuesta, ConfiguracionAplicacion
from ..models.instrumento import Item, Escala, Dimension
from ..utils.decorators import roles_requeridos

aplicacion_bp = Blueprint('aplicaciones', __name__)

# Tiempo máximo que una prueba puede estar en progreso antes de considerarse abandonada
HORAS_EXPIRACION_PRUEBA = 48


def expirar_aplicaciones_abandonadas(usuario_id=None):
    """Marca como 'abandonada' las aplicaciones en_progreso que superaron el límite de tiempo.

    Si se pasa usuario_id, sólo se revisan las aplicaciones de ese usuario.
    Si no se pasa, se hace un barrido global de todos los usuarios.

    Retorna el número de aplicaciones marcadas como abandonadas.
    """
    limite = datetime.utcnow() - timedelta(hours=HORAS_EXPIRACION_PRUEBA)
    query = Aplicacion.query.filter(
        Aplicacion.estado == 'en_progreso',
        Aplicacion.fecha_inicio <= limite,
    )
    if usuario_id is not None:
        query = query.filter(Aplicacion.usuario_id == usuario_id)

    vencidas = query.all()
    for ap in vencidas:
        ap.estado = 'abandonada'

    if vencidas:
        db.session.commit()

    return len(vencidas)


@aplicacion_bp.route('/disponibles', methods=['GET'])
@jwt_required()
def configuraciones_disponibles():
    """Listar configuraciones disponibles para el estudiante.
    
    Regla: por cada instrumento, mostrar solo la config obligatoria (si existe).
    Además, mostrar el seguimiento más reciente (no-obligatoria) entre todos los instrumentos.
    Así el estudiante siempre ve: prueba obligatoria por instrumento + 1 seguimiento activo.
    """
    ahora = datetime.utcnow()
    todas = ConfiguracionAplicacion.query.filter(
        ConfiguracionAplicacion.activa == True,
        ConfiguracionAplicacion.fecha_inicio <= ahora,
        ConfiguracionAplicacion.fecha_fin >= ahora,
    ).order_by(ConfiguracionAplicacion.fecha_inicio.desc()).all()

    # Separar obligatorias y no-obligatorias (seguimiento)
    obligatorias_por_inst = {}
    seguimientos = []
    for c in todas:
        if c.obligatoria:
            # Una sola por instrumento (la primera que encontremos, ya está ordenada desc)
            if c.instrumento_id not in obligatorias_por_inst:
                obligatorias_por_inst[c.instrumento_id] = c
        else:
            seguimientos.append(c)

    resultado = list(obligatorias_por_inst.values())

    # Agregar solo el seguimiento más reciente (el primero por fecha_inicio desc)
    if seguimientos:
        resultado.append(seguimientos[0])

    return jsonify({
        'configuraciones': [c.to_dict() for c in resultado]
    }), 200


@aplicacion_bp.route('/iniciar', methods=['POST'])
@jwt_required()
def iniciar_aplicacion():
    """Iniciar una nueva aplicación del instrumento."""
    usuario_id = int(get_jwt_identity())
    datos = request.get_json()
    configuracion_id = datos.get('configuracion_id')

    if not configuracion_id:
        return jsonify({'error': 'configuracion_id es requerido'}), 400

    # Expirar pruebas que lleven más de HORAS_EXPIRACION_PRUEBA horas sin completarse
    expirar_aplicaciones_abandonadas(usuario_id=usuario_id)

    # Verificar si ya tiene una aplicación en progreso
    existente = Aplicacion.query.filter_by(
        usuario_id=usuario_id,
        configuracion_id=configuracion_id,
        estado='en_progreso'
    ).first()

    if existente:
        return jsonify({
            'message': 'Ya tienes una aplicación en progreso',
            'aplicacion': existente.to_dict(),
        }), 200

    # Verificar si ya completó
    completada = Aplicacion.query.filter_by(
        usuario_id=usuario_id,
        configuracion_id=configuracion_id,
        estado='completada'
    ).first()

    if completada:
        return jsonify({'error': 'Ya completaste esta prueba'}), 400

    aplicacion = Aplicacion(
        usuario_id=usuario_id,
        configuracion_id=configuracion_id,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string,
    )
    db.session.add(aplicacion)
    db.session.commit()

    return jsonify({
        'message': 'Aplicación iniciada',
        'aplicacion': aplicacion.to_dict(),
    }), 201


@aplicacion_bp.route('/<int:id>/respuestas', methods=['POST'])
@jwt_required()
def guardar_respuestas(id):
    """Guardar respuestas (guardado automático progresivo)."""
    usuario_id = int(get_jwt_identity())
    aplicacion = Aplicacion.query.get_or_404(id)

    if aplicacion.usuario_id != usuario_id:
        return jsonify({'error': 'No autorizado'}), 403

    if aplicacion.estado == 'completada':
        return jsonify({'error': 'Esta aplicación ya fue completada'}), 400

    datos = request.get_json(silent=True) or {}
    respuestas_data = datos.get('respuestas', [])
    if not isinstance(respuestas_data, list) or len(respuestas_data) > 30:
        return jsonify({'error': 'Formato de respuestas inválido'}), 400

    instrumento_id = aplicacion.configuracion.instrumento_id
    ids_solicitados = []
    for resp in respuestas_data:
        if not isinstance(resp, dict) or 'item_id' not in resp:
            return jsonify({'error': 'Respuesta inválida'}), 400
        try:
            ids_solicitados.append(int(resp['item_id']))
        except (TypeError, ValueError):
            return jsonify({'error': 'item_id inválido'}), 400
    if len(ids_solicitados) != len(set(ids_solicitados)):
        return jsonify({'error': 'Hay ítems duplicados en la solicitud'}), 400

    if ids_solicitados:
        validos = {
            row[0] for row in db.session.query(Item.id).join(
                Escala, Item.escala_id == Escala.id
            ).join(
                Dimension, Escala.dimension_id == Dimension.id
            ).filter(
                Dimension.instrumento_id == instrumento_id,
                Item.activo == True,
                Item.id.in_(ids_solicitados),
            ).all()
        }
        if validos != set(ids_solicitados):
            return jsonify({'error': 'Una o más respuestas no pertenecen a esta prueba activa'}), 400

    # Cargar todas las respuestas existentes de esta aplicación en un solo query
    # evita N+1: una consulta en lugar de una por cada item del lote
    existentes = {
        r.item_id: r
        for r in Respuesta.query.filter_by(aplicacion_id=id).all()
    }

    for resp in respuestas_data:
        item_id = resp['item_id']
        if item_id in existentes:
            existentes[item_id].valor = resp.get('valor')
            existentes[item_id].valor_texto = resp.get('valor_texto')
            existentes[item_id].tiempo_respuesta_seg = resp.get('tiempo_respuesta_seg')
        else:
            nueva = Respuesta(
                aplicacion_id=id,
                item_id=item_id,
                valor=resp.get('valor'),
                valor_texto=resp.get('valor_texto'),
                tiempo_respuesta_seg=resp.get('tiempo_respuesta_seg'),
            )
            db.session.add(nueva)

    # Contar respuestas guardadas (ya dentro de la transacción actual)
    respondidos = len(existentes) + sum(
        1 for r in respuestas_data if r['item_id'] not in existentes
    )

    # Calcular total de ítems activos con una sola consulta JOIN (evita N+1)
    total_items_instrumento = db.session.query(func.count(Item.id)).join(
        Escala, Item.escala_id == Escala.id
    ).join(
        Dimension, Escala.dimension_id == Dimension.id
    ).filter(
        Dimension.instrumento_id == instrumento_id,
        Item.activo == True,
    ).scalar() or 0

    if total_items_instrumento > 0:
        aplicacion.progreso = min(100, int(respondidos / total_items_instrumento * 100))

    db.session.commit()

    return jsonify({
        'message': 'Respuestas guardadas',
        'progreso': aplicacion.progreso,
        'respondidos': respondidos,
    }), 200


@aplicacion_bp.route('/<int:id>/finalizar', methods=['POST'])
@jwt_required()
def finalizar_aplicacion(id):
    """Finalizar la aplicación cuando se completen todas las respuestas."""
    usuario_id = int(get_jwt_identity())
    aplicacion = Aplicacion.query.get_or_404(id)

    if aplicacion.usuario_id != usuario_id:
        return jsonify({'error': 'No autorizado'}), 403

    if aplicacion.estado == 'completada':
        return jsonify({'error': 'Ya fue completada'}), 400

    # Obtener IDs de ítems obligatorios con una sola consulta JOIN (evita N+1)
    instrumento_id = aplicacion.configuracion.instrumento_id
    items_obligatorios = [
        r[0] for r in db.session.query(Item.id).join(
            Escala, Item.escala_id == Escala.id
        ).join(
            Dimension, Escala.dimension_id == Dimension.id
        ).filter(
            Dimension.instrumento_id == instrumento_id,
            Item.activo == True,
            Item.obligatorio == True,
        ).all()
    ]

    respondidos_ids = set(
        r[0] for r in db.session.query(Respuesta.item_id).filter_by(aplicacion_id=id).all()
    )
    faltantes = [iid for iid in items_obligatorios if iid not in respondidos_ids]

    if faltantes:
        return jsonify({
            'error': 'Hay preguntas obligatorias sin responder',
            'items_faltantes': faltantes,
            'total_faltantes': len(faltantes),
        }), 400

    aplicacion.estado = 'completada'
    aplicacion.fecha_fin = datetime.utcnow()
    aplicacion.progreso = 100
    db.session.commit()

    return jsonify({
        'message': 'Aplicación finalizada exitosamente',
        'aplicacion': aplicacion.to_dict(),
    }), 200


@aplicacion_bp.route('/<int:id>/progreso', methods=['GET'])
@jwt_required()
def obtener_progreso(id):
    """Obtener el progreso actual de una aplicación."""
    usuario_id = int(get_jwt_identity())
    aplicacion = Aplicacion.query.get_or_404(id)

    if aplicacion.usuario_id != usuario_id:
        return jsonify({'error': 'No autorizado'}), 403

    respuestas = aplicacion.respuestas.all()

    return jsonify({
        'aplicacion': aplicacion.to_dict(),
        'respuestas': [r.to_dict() for r in respuestas],
        'total_respondidas': len(respuestas),
    }), 200


@aplicacion_bp.route('/mis-aplicaciones', methods=['GET'])
@jwt_required()
def mis_aplicaciones():
    """Listar las aplicaciones del usuario autenticado."""
    usuario_id = int(get_jwt_identity())

    # Marcar como abandonadas las pruebas en_progreso que superaron el límite de tiempo
    expirar_aplicaciones_abandonadas(usuario_id=usuario_id)

    aplicaciones = Aplicacion.query.filter_by(usuario_id=usuario_id).order_by(
        Aplicacion.created_at.desc()
    ).all()
    return jsonify({
        'aplicaciones': [a.to_dict() for a in aplicaciones]
    }), 200
