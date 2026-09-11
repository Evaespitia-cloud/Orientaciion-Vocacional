"""Controlador de exportación de datos."""

import csv
import io
from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models.aplicacion import Aplicacion, Respuesta
from ..models.instrumento import Item, Escala, Dimension
from ..models.resultado import PerfilVocacional, ResultadoDimension
from ..models.usuario import Usuario
from ..utils.decorators import roles_requeridos, permiso_requerido
from ..utils.audit import registrar_auditoria

exportacion_bp = Blueprint('exportacion', __name__)


@exportacion_bp.route('/csv/resultados', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo', 'investigador')
def exportar_resultados_csv():
    """Exportar resultados en formato CSV."""
    usuario_id = int(get_jwt_identity())
    usuario = Usuario.query.get(usuario_id)
    config_id = request.args.get('configuracion_id', type=int)
    anonimizado = request.args.get('anonimizado', 'true').lower() == 'true'

    # Verificar permisos para datos identificados
    if not anonimizado and usuario.rol.nombre not in ('bienestar', 'ti'):
        return jsonify({'error': 'No tiene permisos para exportar datos identificados'}), 403

    query = Aplicacion.query.filter_by(estado='completada')
    if config_id:
        query = query.filter_by(configuracion_id=config_id)

    aplicaciones = query.all()

    # Pre-cargar datos demográficos de todos los estudiantes involucrados
    from ..models.demografico import DatoDemografico, CampoDemografico
    campos_interes = ['grado_escolar', 'ciudad_region', 'tipo_colegio', 'estrato', 'edad', 'genero']
    campos_map = {
        c.nombre: c.id
        for c in CampoDemografico.query.filter(CampoDemografico.nombre.in_(campos_interes)).all()
    }
    usuario_ids = [a.usuario_id for a in aplicaciones]
    datos_demo_rows = DatoDemografico.query.filter(
        DatoDemografico.usuario_id.in_(usuario_ids),
        DatoDemografico.campo_id.in_(campos_map.values()),
    ).all()
    # demo_index[usuario_id][campo_nombre] = valor
    campo_id_to_nombre = {v: k for k, v in campos_map.items()}
    demo_index: dict = {}
    for d in datos_demo_rows:
        demo_index.setdefault(d.usuario_id, {})[campo_id_to_nombre[d.campo_id]] = d.valor

    def demo(uid, campo):
        return demo_index.get(uid, {}).get(campo, 'N/A')

    # Generar CSV
    output = io.StringIO()
    writer = csv.writer(output)

    if anonimizado:
        writer.writerow(['ID_Aplicacion', 'Grado_Escolar', 'Ciudad_Region',
                         'Tipo_Colegio', 'Estrato', 'Edad', 'Genero',
                         'Cohorte', 'Perfil_Principal', 'Perfil_Secundario', 'Fecha_Aplicacion'])
    else:
        writer.writerow(['ID_Aplicacion', 'Documento', 'Nombres', 'Apellidos', 'Email',
                         'Grado_Escolar', 'Ciudad_Region', 'Tipo_Colegio', 'Estrato',
                         'Edad', 'Genero', 'Cohorte',
                         'Perfil_Principal', 'Perfil_Secundario', 'Fecha_Aplicacion'])

    for app in aplicaciones:
        perfil = PerfilVocacional.query.filter_by(aplicacion_id=app.id).first()
        est = app.usuario
        uid = est.id

        if anonimizado:
            writer.writerow([
                app.id,
                demo(uid, 'grado_escolar'), demo(uid, 'ciudad_region'),
                demo(uid, 'tipo_colegio'), demo(uid, 'estrato'),
                demo(uid, 'edad'), demo(uid, 'genero'),
                est.cohorte or 'N/A',
                perfil.perfil_principal if perfil else 'N/A',
                perfil.perfil_secundario if perfil else 'N/A',
                app.fecha_fin.strftime('%Y-%m-%d') if app.fecha_fin else 'N/A',
            ])
        else:
            writer.writerow([
                app.id, est.documento or 'N/A', est.nombres, est.apellidos, est.email,
                demo(uid, 'grado_escolar'), demo(uid, 'ciudad_region'),
                demo(uid, 'tipo_colegio'), demo(uid, 'estrato'),
                demo(uid, 'edad'), demo(uid, 'genero'),
                est.cohorte or 'N/A',
                perfil.perfil_principal if perfil else 'N/A',
                perfil.perfil_secundario if perfil else 'N/A',
                app.fecha_fin.strftime('%Y-%m-%d') if app.fecha_fin else 'N/A',
            ])

    registrar_auditoria(
        usuario_id, 'EXPORTAR_CSV', 'exportacion',
        f'Exportación CSV {"anonimizada" if anonimizado else "identificada"} - {len(aplicaciones)} registros',
        ip_address=request.remote_addr
    )

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=resultados_orientacion.csv'}
    )


@exportacion_bp.route('/csv/estadisticas', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo')
def exportar_estadisticas_csv():
    """Exportar estadísticas agregadas en CSV."""
    from ..services.estadistica_service import EstadisticaService
    config_id = request.args.get('configuracion_id', type=int)

    output = io.StringIO()
    writer = csv.writer(output)

    # Estadísticas por tipo de colegio
    writer.writerow(['=== ESTADÍSTICAS POR TIPO DE COLEGIO ==='])
    writer.writerow(['Tipo_Colegio', 'Total', 'Completadas', 'Tasa (%)'])
    for r in EstadisticaService.estadisticas_por_grado(config_id):
        writer.writerow([r.get('grado', 'N/A'), r.get('total_aplicaciones', 0),
                          r.get('completadas', 0), r.get('tasa_completacion', 0)])

    writer.writerow([])
    writer.writerow(['=== DISTRIBUCIÓN DE PERFILES ==='])
    writer.writerow(['Perfil', 'Cantidad', 'Porcentaje (%)'])
    for r in EstadisticaService.distribucion_perfiles(config_id):
        writer.writerow([r['perfil'], r['cantidad'], r['porcentaje']])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=estadisticas_orientacion.csv'}
    )


AREAS_RIASEC = ['Realista', 'Investigador', 'Artístico', 'Social', 'Emprendedor', 'Convencional']
CODIGO_AREA = {'Realista': 'R', 'Investigador': 'I', 'Artístico': 'A', 'Social': 'S', 'Emprendedor': 'E', 'Convencional': 'C'}


def _respuesta_visible_y_campo(item, respuesta):
    """Texto legible de la respuesta y el campo RIASEC asociado, para la hoja de trazabilidad."""
    if respuesta is None or respuesta.valor is None:
        return 'Sin responder', None
    if item.tipo == 'comparacion_binaria':
        ops = item.opciones or {}
        clave = 'opcion_a' if respuesta.valor == 0 else 'opcion_b'
        opcion = ops.get(clave, {})
        return opcion.get('texto', ''), opcion.get('campo')
    if item.tipo == 'juicio_situacional':
        opciones = (item.opciones or {}).get('opciones', [])
        try:
            idx = int(respuesta.valor)
        except (TypeError, ValueError):
            return str(respuesta.valor), item.escala.nombre if item.escala else None
        if 0 <= idx < len(opciones):
            return f"{opciones[idx].get('letra', '')}) {opciones[idx].get('texto', '')}", (item.escala.nombre if item.escala else None)
        return str(respuesta.valor), item.escala.nombre if item.escala else None
    return str(respuesta.valor), item.escala.nombre if item.escala else None


def _puntaje_obtenido(item, respuesta):
    from ..services.psicometrico_service import PsicometricoService
    if respuesta is None:
        return 0
    return sum(p for _area, p in PsicometricoService._contribuciones(item, respuesta))


@exportacion_bp.route('/excel/completo', methods=['GET'])
@jwt_required()
@roles_requeridos('bienestar', 'ti', 'directivo', 'investigador')
def exportar_excel_completo():
    """Exporta un Excel con la estructura mínima de la base de datos exportable
    definida en los lineamientos de la versión de simulación: identificación,
    aplicación, respuestas por ítem (trazabilidad), intereses, competencias y
    perfil integrado.
    """
    try:
        from openpyxl import Workbook
    except ImportError:
        return jsonify({'error': 'openpyxl no está instalado en el servidor'}), 500

    usuario_id = int(get_jwt_identity())
    config_id = request.args.get('configuracion_id', type=int)

    query = Aplicacion.query.filter_by(estado='completada')
    if config_id:
        query = query.filter_by(configuracion_id=config_id)
    aplicaciones = query.all()

    from ..models.demografico import DatoDemografico, CampoDemografico
    campos_interes = ['grado_escolar', 'grupo', 'edad']
    campos_map = {c.nombre: c.id for c in CampoDemografico.query.filter(CampoDemografico.nombre.in_(campos_interes)).all()}
    usuario_ids = [a.usuario_id for a in aplicaciones]
    datos_demo_rows = DatoDemografico.query.filter(
        DatoDemografico.usuario_id.in_(usuario_ids),
        DatoDemografico.campo_id.in_(campos_map.values()),
    ).all() if usuario_ids else []
    campo_id_to_nombre = {v: k for k, v in campos_map.items()}
    demo_index: dict = {}
    for d in datos_demo_rows:
        demo_index.setdefault(d.usuario_id, {})[campo_id_to_nombre[d.campo_id]] = d.valor

    def demo(uid, campo):
        return demo_index.get(uid, {}).get(campo, '')

    wb = Workbook()

    ws_id = wb.active
    ws_id.title = 'Identificacion'
    ws_id.append(['id_aplicacion', 'id_estudiante', 'institucion', 'grado', 'grupo', 'edad', 'fecha_aplicacion'])

    ws_app = wb.create_sheet('Aplicacion')
    ws_app.append(['id_aplicacion', 'version_prueba', 'fecha_inicio', 'fecha_fin', 'tiempo_total_seg', 'dispositivo'])

    ws_resp = wb.create_sheet('Respuestas')
    ws_resp.append([
        'id_aplicacion', 'codigo_item', 'respuesta_visible', 'respuesta_original',
        'campo_asociado', 'puntaje_obtenido', 'orden_item', 'version_item', 'estado_item',
    ])

    ws_int = wb.create_sheet('Intereses')
    ws_int.append(['id_aplicacion'] + [f'puntaje_{CODIGO_AREA[a]}' for a in AREAS_RIASEC] + ['ranking_riasec'])

    ws_comp = wb.create_sheet('Competencias')
    ws_comp.append(['id_aplicacion'] + [f'puntaje_{CODIGO_AREA[a]}' for a in AREAS_RIASEC] + [f'porcentaje_{CODIGO_AREA[a]}' for a in AREAS_RIASEC])

    ws_perfil = wb.create_sheet('PerfilIntegrado')
    ws_perfil.append(['id_aplicacion', 'campo_prioritario_1', 'campo_prioritario_2', 'campo_prioritario_3', 'interpretacion_generada'])

    for app in aplicaciones:
        est = app.usuario
        uid = est.id
        institucion_nombre = est.grado.institucion.nombre if est.grado and est.grado.institucion else ''
        grado_nombre = est.grado.nombre if est.grado else demo(uid, 'grado_escolar')

        ws_id.append([
            app.id, uid, institucion_nombre, grado_nombre, demo(uid, 'grupo'), demo(uid, 'edad'),
            app.fecha_inicio.strftime('%Y-%m-%d') if app.fecha_inicio else '',
        ])

        tiempo_total = None
        if app.fecha_inicio and app.fecha_fin:
            tiempo_total = int((app.fecha_fin - app.fecha_inicio).total_seconds())
        ws_app.append([
            app.id, app.configuracion.instrumento.version if app.configuracion else '',
            app.fecha_inicio.isoformat() if app.fecha_inicio else '',
            app.fecha_fin.isoformat() if app.fecha_fin else '',
            tiempo_total, app.user_agent or '',
        ])

        respuestas = {r.item_id: r for r in Respuesta.query.filter_by(aplicacion_id=app.id).all()}
        items = Item.query.join(Escala).join(Dimension).filter(
            Dimension.instrumento_id == app.configuracion.instrumento_id
        ).order_by(Item.orden).all()
        for item in items:
            r = respuestas.get(item.id)
            visible, campo = _respuesta_visible_y_campo(item, r)
            ws_resp.append([
                app.id, item.codigo or item.id, visible,
                r.valor if r else '', campo or '', _puntaje_obtenido(item, r),
                item.orden, item.version, 'activo' if item.activo else 'inactivo',
            ])

        perfil = PerfilVocacional.query.filter_by(aplicacion_id=app.id).first()
        datos = (perfil.datos_json or {}) if perfil else {}
        puntajes_por_area = datos.get('puntajes_por_area', {})

        ws_int.append([app.id] + [puntajes_por_area.get(a, {}).get('interes_puntaje', 0) for a in AREAS_RIASEC] + [
            ','.join(datos.get('ranking_intereses', []))
        ])
        ws_comp.append(
            [app.id]
            + [puntajes_por_area.get(a, {}).get('competencia_puntaje', 0) for a in AREAS_RIASEC]
            + [puntajes_por_area.get(a, {}).get('competencia_porcentaje', 0) for a in AREAS_RIASEC]
        )
        ws_perfil.append([
            app.id, datos.get('campo_prioritario_1', ''), datos.get('campo_prioritario_2', ''),
            datos.get('campo_prioritario_3', ''), datos.get('interpretacion_generada', ''),
        ])

    registrar_auditoria(
        usuario_id, 'EXPORTAR_EXCEL', 'exportacion',
        f'Exportación Excel completa - {len(aplicaciones)} aplicaciones',
        ip_address=request.remote_addr
    )

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return Response(
        buffer.getvalue(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=orientacion_vocacional_simulacion.xlsx'}
    )
