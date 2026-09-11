"""Controlador de formulario demográfico — CRUD de campos y datos de estudiantes."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import db
from ..models.demografico import CampoDemografico, DatoDemografico, FormulaCalculo
from ..utils.decorators import roles_requeridos
from ..utils.audit import registrar_auditoria

demografico_bp = Blueprint('demografico', __name__)


# =====================================================
# CAMPOS DEMOGRÁFICOS (Admin)
# =====================================================

@demografico_bp.route('/campos', methods=['GET'])
@jwt_required()
def listar_campos():
    """Listar todos los campos demográficos activos."""
    solo_activos = request.args.get('activos', 'true').lower() == 'true'
    query = CampoDemografico.query
    if solo_activos:
        query = query.filter_by(activo=True)
    campos = query.order_by(CampoDemografico.orden).all()
    return jsonify({'campos': [c.to_dict() for c in campos]}), 200


@demografico_bp.route('/campos', methods=['POST'])
@jwt_required()
@roles_requeridos('bienestar', 'ti')
def crear_campo():
    """Crear un nuevo campo demográfico."""
    datos = request.get_json()
    usuario_id = int(get_jwt_identity())

    campo = CampoDemografico(
        nombre=datos['nombre'],
        etiqueta=datos['etiqueta'],
        tipo_campo=datos.get('tipo_campo', 'texto'),
        opciones=datos.get('opciones'),
        obligatorio=datos.get('obligatorio', True),
        orden=datos.get('orden', 0),
    )
    db.session.add(campo)
    db.session.commit()

    registrar_auditoria(
        usuario_id, 'CREAR_CAMPO_DEMOGRAFICO', 'demografico',
        f'Campo "{campo.etiqueta}" creado',
        ip_address=request.remote_addr
    )

    return jsonify({'message': 'Campo creado', 'campo': campo.to_dict()}), 201


@demografico_bp.route('/campos/<int:id>', methods=['PUT'])
@jwt_required()
@roles_requeridos('bienestar', 'ti')
def actualizar_campo(id):
    """Actualizar un campo demográfico existente."""
    campo = CampoDemografico.query.get_or_404(id)
    datos = request.get_json()
    usuario_id = int(get_jwt_identity())

    if 'etiqueta' in datos:
        campo.etiqueta = datos['etiqueta']
    if 'tipo_campo' in datos:
        campo.tipo_campo = datos['tipo_campo']
    if 'opciones' in datos:
        campo.opciones = datos['opciones']
    if 'obligatorio' in datos:
        campo.obligatorio = datos['obligatorio']
    if 'orden' in datos:
        campo.orden = datos['orden']
    if 'activo' in datos:
        campo.activo = datos['activo']

    db.session.commit()

    registrar_auditoria(
        usuario_id, 'ACTUALIZAR_CAMPO_DEMOGRAFICO', 'demografico',
        f'Campo "{campo.etiqueta}" actualizado',
        ip_address=request.remote_addr
    )

    return jsonify({'message': 'Campo actualizado', 'campo': campo.to_dict()}), 200


@demografico_bp.route('/campos/<int:id>', methods=['DELETE'])
@jwt_required()
@roles_requeridos('ti')
def eliminar_campo(id):
    """Desactivar un campo demográfico (soft delete)."""
    campo = CampoDemografico.query.get_or_404(id)
    usuario_id = int(get_jwt_identity())

    campo.activo = False
    db.session.commit()

    registrar_auditoria(
        usuario_id, 'ELIMINAR_CAMPO_DEMOGRAFICO', 'demografico',
        f'Campo "{campo.etiqueta}" desactivado',
        ip_address=request.remote_addr
    )

    return jsonify({'message': 'Campo desactivado'}), 200


# =====================================================
# DATOS DEMOGRÁFICOS (Estudiante)
# =====================================================

@demografico_bp.route('/datos', methods=['GET'])
@jwt_required()
def obtener_mis_datos():
    """Obtener datos demográficos del usuario autenticado."""
    usuario_id = int(get_jwt_identity())
    datos = DatoDemografico.query.filter_by(usuario_id=usuario_id).all()
    return jsonify({'datos': [d.to_dict() for d in datos]}), 200


@demografico_bp.route('/datos', methods=['POST'])
@jwt_required()
def guardar_datos():
    """Guardar o actualizar datos demográficos del estudiante."""
    usuario_id = int(get_jwt_identity())
    datos = request.get_json()
    respuestas = datos.get('respuestas', [])

    for resp in respuestas:
        campo_id = resp.get('campo_id')
        valor = resp.get('valor', '').strip()

        # Validar que el campo existe y está activo
        campo = CampoDemografico.query.filter_by(id=campo_id, activo=True).first()
        if not campo:
            continue

        # Validar campo obligatorio
        if campo.obligatorio and not valor:
            return jsonify({
                'error': f'El campo "{campo.etiqueta}" es obligatorio'
            }), 400

        # Upsert
        existente = DatoDemografico.query.filter_by(
            usuario_id=usuario_id,
            campo_id=campo_id
        ).first()

        if existente:
            existente.valor = valor
        else:
            nuevo = DatoDemografico(
                usuario_id=usuario_id,
                campo_id=campo_id,
                valor=valor,
            )
            db.session.add(nuevo)

    db.session.commit()
    return jsonify({'message': 'Datos demográficos guardados'}), 200


@demografico_bp.route('/datos/usuario/<int:usuario_id>', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti')
def obtener_datos_usuario(usuario_id):
    """Obtener datos demográficos de un usuario específico (admin)."""
    datos = DatoDemografico.query.filter_by(usuario_id=usuario_id).all()
    return jsonify({'datos': [d.to_dict() for d in datos]}), 200


@demografico_bp.route('/datos/todos', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo')
def listar_todos_datos():
    """Listar todos los estudiantes con sus datos demográficos (admin)."""
    from ..models.usuario import Usuario, Rol

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    buscar = request.args.get('buscar', '').strip()

    # Obtener el rol 'estudiante'
    rol_est = Rol.query.filter_by(nombre='estudiante').first()
    query = Usuario.query
    if rol_est:
        query = query.filter_by(rol_id=rol_est.id)

    if buscar:
        query = query.filter(
            db.or_(
                Usuario.nombres.ilike(f'%{buscar}%'),
                Usuario.apellidos.ilike(f'%{buscar}%'),
                Usuario.email.ilike(f'%{buscar}%'),
                Usuario.documento.ilike(f'%{buscar}%'),
            )
        )

    paginacion = query.order_by(Usuario.nombres).paginate(
        page=page, per_page=per_page, error_out=False
    )

    campos = CampoDemografico.query.filter_by(activo=True).order_by(CampoDemografico.orden).all()

    estudiantes = []
    for u in paginacion.items:
        datos = {str(d.campo_id): d.valor for d in DatoDemografico.query.filter_by(usuario_id=u.id).all()}
        estudiantes.append({
            'id': u.id,
            'nombre_completo': f'{u.nombres} {u.apellidos}',
            'email': u.email,
            'documento': u.documento,
            'datos': datos,
        })

    return jsonify({
        'estudiantes': estudiantes,
        'campos': [c.to_dict() for c in campos],
        'total': paginacion.total,
        'paginas': paginacion.pages,
        'pagina_actual': page,
    }), 200


@demografico_bp.route('/datos/completo', methods=['GET'])
@jwt_required()
def verificar_datos_completos():
    """Verificar si el estudiante ya completó los datos demográficos obligatorios."""
    usuario_id = int(get_jwt_identity())
    campos_obligatorios = CampoDemografico.query.filter_by(activo=True, obligatorio=True).all()
    datos_usuario = {d.campo_id: d.valor for d in DatoDemografico.query.filter_by(usuario_id=usuario_id).all()}

    faltantes = []
    for campo in campos_obligatorios:
        if campo.id not in datos_usuario or not datos_usuario[campo.id]:
            faltantes.append(campo.to_dict())

    return jsonify({
        'completo': len(faltantes) == 0,
        'campos_faltantes': faltantes,
    }), 200


# =====================================================
# FÓRMULAS DE CÁLCULO (Admin)
# =====================================================

@demografico_bp.route('/formulas', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti')
def listar_formulas():
    """Listar fórmulas de cálculo."""
    formulas = FormulaCalculo.query.all()
    return jsonify({'formulas': [f.to_dict() for f in formulas]}), 200


@demografico_bp.route('/formulas', methods=['POST'])
@jwt_required()
@roles_requeridos('ti')
def crear_formula():
    """Crear una nueva fórmula de cálculo."""
    datos = request.get_json()

    formula = FormulaCalculo(
        nombre=datos['nombre'],
        descripcion=datos.get('descripcion'),
        tipo=datos.get('tipo', 'holland_riasec'),
        parametros=datos.get('parametros', {}),
    )
    db.session.add(formula)
    db.session.commit()

    return jsonify({'message': 'Fórmula creada', 'formula': formula.to_dict()}), 201


@demografico_bp.route('/formulas/<int:id>', methods=['PUT'])
@jwt_required()
@roles_requeridos('ti')
def actualizar_formula(id):
    """Actualizar una fórmula de cálculo."""
    formula = FormulaCalculo.query.get_or_404(id)
    datos = request.get_json()

    if 'nombre' in datos:
        formula.nombre = datos['nombre']
    if 'descripcion' in datos:
        formula.descripcion = datos['descripcion']
    if 'parametros' in datos:
        formula.parametros = datos['parametros']
    if 'activa' in datos:
        formula.activa = datos['activa']

    db.session.commit()
    return jsonify({'message': 'Fórmula actualizada', 'formula': formula.to_dict()}), 200
