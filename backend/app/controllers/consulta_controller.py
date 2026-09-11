"""Controlador de consulta de resultados individuales."""

from collections import Counter
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models.aplicacion import Aplicacion
from ..models.resultado import PerfilVocacional, ResultadoDimension
from ..models.usuario import Usuario
from ..models.demografico import CampoDemografico, DatoDemografico
from ..utils.decorators import roles_requeridos

consulta_bp = Blueprint('consultas', __name__)


@consulta_bp.route('/resultado/<int:aplicacion_id>', methods=['GET'])
@jwt_required()
def consultar_resultado(aplicacion_id):
    """Consultar resultado individual de una aplicación."""
    usuario_id = int(get_jwt_identity())
    aplicacion = Aplicacion.query.get_or_404(aplicacion_id)
    usuario = Usuario.query.get(usuario_id)

    # Verificar permisos
    if aplicacion.usuario_id != usuario_id and usuario.rol.nombre not in ('bienestar', 'ti', 'directivo'):
        return jsonify({'error': 'No autorizado'}), 403

    perfil = PerfilVocacional.query.filter_by(aplicacion_id=aplicacion_id).first()
    resultados_dim = ResultadoDimension.query.filter_by(aplicacion_id=aplicacion_id).all()

    return jsonify({
        'aplicacion': aplicacion.to_dict(),
        'perfil': perfil.to_dict() if perfil else None,
        'resultados_dimension': [r.to_dict() for r in resultados_dim],
        'estudiante': aplicacion.usuario.to_dict(),
    }), 200


@consulta_bp.route('/estudiante/<int:estudiante_id>', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo')
def consultar_estudiante(estudiante_id):
    """Consultar todas las aplicaciones y resultados de un estudiante."""
    estudiante = Usuario.query.get_or_404(estudiante_id)
    aplicaciones = Aplicacion.query.filter_by(usuario_id=estudiante_id).order_by(
        Aplicacion.created_at.desc()
    ).all()

    resultados = []
    for app in aplicaciones:
        perfil = PerfilVocacional.query.filter_by(aplicacion_id=app.id).first()
        resultados.append({
            'aplicacion': app.to_dict(),
            'perfil': perfil.to_dict() if perfil else None,
        })

    return jsonify({
        'estudiante': estudiante.to_dict(),
        'aplicaciones': resultados,
    }), 200


@consulta_bp.route('/buscar', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo')
def buscar_resultados():
    """Buscar resultados por estudiante, mostrando el perfil más predominante y el estado de cada prueba."""
    buscar   = request.args.get('buscar', '').strip()
    perfil   = request.args.get('perfil', '').strip()
    page     = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    from ..extensions import db
    from ..models.usuario import Rol
    from ..models.aplicacion import ConfiguracionAplicacion

    # Clasificar configs: obligatorias por instrumento → Intereses vs Competencias,
    # y no obligatorias → Seguimiento periódico
    todas_configs = ConfiguracionAplicacion.query.all()
    cfg_intereses_ids    = set()
    cfg_competencias_ids = set()
    cfg_seguimiento_ids  = set()
    for c in todas_configs:
        nombre_inst = (c.instrumento.nombre or '') if c.instrumento else ''
        if c.obligatoria and 'nteres' in nombre_inst:
            cfg_intereses_ids.add(c.id)
        elif c.obligatoria and 'ompet' in nombre_inst:
            cfg_competencias_ids.add(c.id)
        elif not c.obligatoria:
            cfg_seguimiento_ids.add(c.id)

    # Query base: TODOS los estudiantes activos
    student_query = (
        db.session.query(Usuario)
        .join(Rol, Rol.id == Usuario.rol_id)
        .filter(Rol.nombre == 'estudiante', Usuario.activo == True)
    )

    if buscar:
        like = f'%{buscar}%'
        student_query = student_query.filter(
            (Usuario.nombres.ilike(like)) |
            (Usuario.apellidos.ilike(like)) |
            (Usuario.email.ilike(like))
        )

    student_query = student_query.order_by(Usuario.apellidos.asc(), Usuario.nombres.asc())
    todos_estudiantes = student_query.all()

    # Cargar todas las apps de estos estudiantes en una sola consulta
    ids_estudiantes = [e.id for e in todos_estudiantes]
    todas_apps = (
        Aplicacion.query
        .filter(Aplicacion.usuario_id.in_(ids_estudiantes))
        .order_by(Aplicacion.usuario_id, Aplicacion.fecha_fin.desc())
        .all()
    )
    # Agrupar apps por usuario
    apps_por_usuario = {}
    for app in todas_apps:
        apps_por_usuario.setdefault(app.usuario_id, []).append(app)

    def _estado_cfg(apps_usuario, config_ids):
        """Devuelve el estado de la app más reciente, priorizando 'completada'."""
        for app in apps_usuario:
            if app.configuracion_id in config_ids and app.estado == 'completada':
                return 'completada'
        for app in apps_usuario:
            if app.configuracion_id in config_ids:
                return app.estado
        return 'sin_iniciar'

    def _ultimo_perfil(apps_usuario):
        """Devuelve el perfil de la aplicación completada más reciente."""
        ultima_fecha = None
        ultima_app_id = None
        ultimo_riasec = None
        ultimo_perfil = None
        
        apps_completadas = [app for app in apps_usuario if app.estado == 'completada']
        apps_completadas.sort(key=lambda a: a.fecha_fin.replace(tzinfo=None) if a.fecha_fin else datetime.min, reverse=True)
        
        if apps_completadas:
            ultima_app = apps_completadas[0]
            p = PerfilVocacional.query.filter_by(aplicacion_id=ultima_app.id).first()
            if p and p.perfil_principal:
                ultimo_perfil = p.perfil_principal
                ultima_fecha = ultima_app.fecha_fin
                ultima_app_id = ultima_app.id
                if p.datos_json:
                    ultimo_riasec = p.datos_json.get('codigo_riasec')
                    
        return ultimo_perfil, ultima_fecha, ultima_app_id, ultimo_riasec

    # Construir resultados
    resultados_raw = []
    for est in todos_estudiantes:
        apps_est = apps_por_usuario.get(est.id, [])
        ultimo_perfil, ultima_fecha, ultima_app_id, ultimo_riasec = _ultimo_perfil(apps_est)
        if perfil and ultimo_perfil != perfil:
            continue
        resultados_raw.append({
            'est': est,
            'perfil_principal': ultimo_perfil,
            'ultima_fecha': ultima_fecha,
            'ultima_app_id': ultima_app_id,
            'codigo_riasec': ultimo_riasec,
            'estado_intereses':    _estado_cfg(apps_est, set(cfg_intereses_ids)),
            'estado_competencias': _estado_cfg(apps_est, set(cfg_competencias_ids)),
            'estado_seguimiento':  _estado_cfg(apps_est, set(cfg_seguimiento_ids)),
        })

    total = len(resultados_raw)
    start = (page - 1) * per_page
    pagina = resultados_raw[start:start + per_page]
    paginas = max(1, (total + per_page - 1) // per_page)

    # Enriquecer grado desde datos_demograficos
    def _normalizar_grado(valor):
        if not valor:
            return None
        txt = str(valor).strip().lower()
        if txt.startswith('9') or 'nov' in txt:
            return '9°'
        if txt.startswith('10') or 'dec' in txt or 'diec' in txt:
            return '10°'
        if txt.startswith('11') or 'once' in txt:
            return '11°'
        return None  # retornar None si no es un grado de colegio válido

    campo_grado = CampoDemografico.query.filter_by(nombre='grado_escolar').first()
    ids_pagina = [r['est'].id for r in pagina]
    demo_grado_map = {}
    if campo_grado and ids_pagina:
        demos = DatoDemografico.query.filter(
            DatoDemografico.campo_id == campo_grado.id,
            DatoDemografico.usuario_id.in_(ids_pagina)
        ).all()
        demo_grado_map = {d.usuario_id: d.valor for d in demos}

    resultados = []
    for r in pagina:
        est = r['est']
        est_dict = est.to_dict()
        # Enriquecer grado
        grado = _normalizar_grado(est_dict.get('grado_nombre'))
        if not grado:
            grado = _normalizar_grado(demo_grado_map.get(est.id))
        if not grado:
            grado = '11°'  # Fallback estándar
        est_dict['grado_nombre'] = grado

        ultima_fecha_str = r['ultima_fecha'].isoformat() if r['ultima_fecha'] else None
        resultados.append({
            'aplicacion': {'id': r['ultima_app_id']},
            'estudiante': est_dict,
            'perfil_principal': r['perfil_principal'],
            'codigo_riasec': r['codigo_riasec'],
            'ultima_fecha': ultima_fecha_str,
            'estado_intereses':    r['estado_intereses'],
            'estado_competencias': r['estado_competencias'],
            'estado_seguimiento':  r['estado_seguimiento'],
        })

    return jsonify({
        'resultados': resultados,
        'total': total,
        'paginas': paginas,
        'pagina_actual': page,
    }), 200
