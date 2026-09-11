"""Controlador de instrumentos psicométricos."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import db
from ..models.instrumento import Instrumento, Dimension, Escala, Item
from ..models.usuario import Usuario
from ..utils.decorators import roles_requeridos
from ..utils.audit import registrar_auditoria

instrumento_bp = Blueprint('instrumentos', __name__)

# Roles que administran el banco de ítems y pueden ver la clave de puntuación
ROLES_CON_CLAVE = ('bienestar', 'ti', 'investigador', 'directivo')


@instrumento_bp.route('/', methods=['GET'])
@jwt_required()
def listar_instrumentos():
    """Listar todos los instrumentos psicométricos."""
    instrumentos = Instrumento.query.filter_by(activo=True).all()
    return jsonify({
        'instrumentos': [i.to_dict(include_dimensiones=False) for i in instrumentos]
    }), 200


@instrumento_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def obtener_instrumento(id):
    """Obtener un instrumento con todas sus dimensiones, escalas e ítems.

    La clave de puntuación (puntaje de cada opción) sólo se expone a roles
    administrativos; a los estudiantes se les oculta para no filtrar la
    calificación de los ítems de juicio situacional.
    """
    instrumento = Instrumento.query.get_or_404(id)
    usuario_id = int(get_jwt_identity())
    usuario = Usuario.query.get(usuario_id)
    incluir_clave = bool(usuario and usuario.rol and usuario.rol.nombre in ROLES_CON_CLAVE)
    return jsonify({
        'instrumento': instrumento.to_dict(include_dimensiones=True, incluir_clave=incluir_clave)
    }), 200


@instrumento_bp.route('/', methods=['POST'])
@jwt_required()
@roles_requeridos('bienestar', 'ti')
def crear_instrumento():
    """Crear un nuevo instrumento psicométrico."""
    datos = request.get_json()
    usuario_id = int(get_jwt_identity())

    instrumento = Instrumento(
        nombre=datos['nombre'],
        descripcion=datos.get('descripcion'),
        version=datos.get('version', '1.0'),
        creado_por=usuario_id,
    )
    db.session.add(instrumento)
    db.session.commit()

    registrar_auditoria(
        usuario_id, 'CREAR_INSTRUMENTO', 'instrumentos',
        f'Instrumento "{instrumento.nombre}" creado',
        ip_address=request.remote_addr
    )

    return jsonify({
        'message': 'Instrumento creado',
        'instrumento': instrumento.to_dict()
    }), 201


@instrumento_bp.route('/<int:id>/dimensiones', methods=['POST'])
@jwt_required()
@roles_requeridos('bienestar', 'ti')
def crear_dimension(id):
    """Agregar una dimensión a un instrumento."""
    instrumento = Instrumento.query.get_or_404(id)
    datos = request.get_json()

    dimension = Dimension(
        instrumento_id=instrumento.id,
        nombre=datos['nombre'],
        descripcion=datos.get('descripcion'),
        peso=datos.get('peso', 1.0),
        orden=datos.get('orden', 0),
    )
    db.session.add(dimension)
    db.session.commit()

    return jsonify({
        'message': 'Dimensión creada',
        'dimension': dimension.to_dict()
    }), 201


@instrumento_bp.route('/dimensiones/<int:dim_id>/escalas', methods=['POST'])
@jwt_required()
@roles_requeridos('bienestar', 'ti')
def crear_escala(dim_id):
    """Agregar una escala a una dimensión."""
    dimension = Dimension.query.get_or_404(dim_id)
    datos = request.get_json()

    escala = Escala(
        dimension_id=dimension.id,
        nombre=datos['nombre'],
        descripcion=datos.get('descripcion'),
        valor_minimo=datos.get('valor_minimo', 1),
        valor_maximo=datos.get('valor_maximo', 5),
        orden=datos.get('orden', 0),
    )
    db.session.add(escala)
    db.session.commit()

    return jsonify({
        'message': 'Escala creada',
        'escala': escala.to_dict()
    }), 201


@instrumento_bp.route('/escalas/<int:esc_id>/items', methods=['POST'])
@jwt_required()
@roles_requeridos('bienestar', 'ti')
def crear_item(esc_id):
    """Agregar un ítem a una escala."""
    escala = Escala.query.get_or_404(esc_id)
    datos = request.get_json(silent=True) or {}
    if not str(datos.get('texto') or '').strip():
        return jsonify({'error': 'El texto del ítem es requerido'}), 400

    item = Item(
        escala_id=escala.id,
        codigo=datos.get('codigo'),
        texto=datos['texto'],
        contexto=datos.get('contexto'),
        tipo=datos.get('tipo', 'likert'),
        opciones=datos.get('opciones'),
        obligatorio=datos.get('obligatorio', True),
        orden=datos.get('orden', 0),
        version=datos.get('version', '1.0'),
    )
    db.session.add(item)
    db.session.commit()

    return jsonify({
        'message': 'Ítem creado',
        'item': item.to_dict()
    }), 201


@instrumento_bp.route('/items/<int:item_id>', methods=['PUT'])
@jwt_required()
@roles_requeridos('bienestar', 'ti')
def actualizar_item(item_id):
    """Actualizar un ítem y validar la estructura de sus respuestas."""
    item = Item.query.get_or_404(item_id)
    datos = request.get_json()

    if 'opciones' in datos:
        opciones = datos['opciones']
        tipo = datos.get('tipo', item.tipo)
        if tipo == 'comparacion_binaria':
            if not isinstance(opciones, dict) or any(
                not isinstance(opciones.get(clave), dict)
                or not opciones[clave].get('campo')
                or not opciones[clave].get('texto')
                for clave in ('opcion_a', 'opcion_b')
            ):
                return jsonify({'error': 'La comparación debe tener dos respuestas completas.'}), 400
        elif tipo == 'juicio_situacional':
            lista = opciones.get('opciones') if isinstance(opciones, dict) else None
            puntajes = [opcion.get('puntaje') for opcion in lista or [] if isinstance(opcion, dict)]
            if (
                len(lista or []) != 4
                or {opcion.get('letra') for opcion in lista or [] if isinstance(opcion, dict)} != set('ABCD')
                or set(puntajes) != {1, 2, 3, 4}
                or any(not opcion.get('texto') for opcion in lista if isinstance(opcion, dict))
            ):
                return jsonify({'error': 'El juicio situacional debe tener opciones A-D con puntajes 1, 2, 3 y 4.'}), 400

    if 'codigo' in datos:
        item.codigo = datos['codigo']
    if 'texto' in datos:
        item.texto = datos['texto']
    if 'contexto' in datos:
        item.contexto = datos['contexto']
    if 'tipo' in datos:
        item.tipo = datos['tipo']
    if 'opciones' in datos:
        item.opciones = datos['opciones']
    if 'obligatorio' in datos:
        item.obligatorio = datos['obligatorio']
    if 'orden' in datos:
        item.orden = datos['orden']
    if 'activo' in datos:
        item.activo = datos['activo']
    if 'version' in datos:
        item.version = datos['version']

    db.session.commit()
    return jsonify({'message': 'Ítem actualizado', 'item': item.to_dict()}), 200


@instrumento_bp.route('/items/<int:item_id>', methods=['DELETE'])
@jwt_required()
@roles_requeridos('bienestar', 'ti')
def eliminar_item(item_id):
    """Desactivar un ítem sin destruir respuestas históricas."""
    item = Item.query.get_or_404(item_id)
    usuario_id = int(get_jwt_identity())
    texto_preview = item.texto[:60]
    item.activo = False
    db.session.commit()
    registrar_auditoria(
        usuario_id, 'ELIMINAR_ITEM', 'items',
        f'Ítem desactivado: "{texto_preview}"',
        ip_address=request.remote_addr
    )
    return jsonify({'message': 'Ítem desactivado'}), 200


@instrumento_bp.route('/items', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo', 'investigador')
def listar_items():
    """Listar ítems con filtros: instrumento_id, escala_id, area, buscar."""
    from ..models.instrumento import Instrumento, Dimension, Escala, Item
    from sqlalchemy import or_

    instrumento_id = request.args.get('instrumento_id', type=int)
    escala_id = request.args.get('escala_id', type=int)
    area = request.args.get('area', '').strip()
    buscar = request.args.get('buscar', '').strip()

    query = Item.query.join(Escala).join(Dimension).join(Instrumento)
    incluir_inactivos = request.args.get('incluir_inactivos', 'false').lower() == 'true'
    if not incluir_inactivos:
        query = query.filter(Item.activo == True)

    if instrumento_id:
        query = query.filter(Instrumento.id == instrumento_id)
    if escala_id:
        query = query.filter(Item.escala_id == escala_id)
    if area:
        query = query.filter(Escala.nombre.ilike(f'%{area}%'))
    if buscar:
        query = query.filter(Item.texto.ilike(f'%{buscar}%'))

    items = query.order_by(Dimension.orden, Escala.orden, Item.orden).all()

    return jsonify({
        'items': [
            {
                **i.to_dict(),
                'escala_nombre': i.escala.nombre,
                'instrumento_nombre': i.escala.dimension.instrumento.nombre,
                'dimension_nombre': i.escala.dimension.nombre,
                'escala_id': i.escala_id,
            }
            for i in items
        ],
        'total': len(items)
    }), 200
