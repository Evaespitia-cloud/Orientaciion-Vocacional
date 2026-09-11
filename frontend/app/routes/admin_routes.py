from flask import Blueprint, render_template, request, redirect, url_for, session, flash, Response as FlaskResponse
from ..utils import api_request, api_requests_parallel, api_request_file, jwt_is_expired

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    """Decorador para requerir rol administrativo. Verifica expiración localmente."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        token = session.get('access_token')
        if not token:
            return redirect(url_for('auth.login'))
        if session.get('rol') not in ('bienestar', 'ti', 'directivo', 'investigador'):
            flash('No tiene permisos para acceder a esta sección.', 'error')
            return redirect(url_for('estudiante.inicio'))
        if jwt_is_expired(token):
            session.clear()
            flash('Su sesión ha expirado. Por favor inicie sesión nuevamente.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def solo_gestion(f):
    """Decorador para rutas de gestión (usuarios, instrumentos, fórmulas) — bloquea investigador."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('rol') == 'investigador':
            flash('No tiene permisos para acceder a esta sección.', 'error')
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Panel administrativo principal."""
    r = api_requests_parallel([
        ('resumen',      'GET', '/estadisticas/resumen'),
        ('participacion','GET', '/estadisticas/participacion'),
        ('perfiles',     'GET', '/estadisticas/perfiles'),
        ('instituciones','GET', '/estadisticas/por-institucion'),
        ('dimensiones',  'GET', '/estadisticas/dimensiones'),
        ('inst',         'GET', '/estadisticas/por-instrumento'),
        ('perf_inst',    'GET', '/estadisticas/perfiles-por-instrumento'),
        ('seg_genero',   'GET', '/estadisticas/segmentacion/genero'),
        ('seg_edad',     'GET', '/estadisticas/segmentacion/edad'),
    ])

    return render_template('admin/dashboard.html',
                           rol=session.get('rol', ''),
                           resumen=r['resumen'][0],
                           participacion=r['participacion'][0],
                           perfiles=r['perfiles'][0].get('distribucion', []),
                           instituciones=r['instituciones'][0].get('instituciones', []),
                           dimensiones=r['dimensiones'][0].get('dimensiones', []),
                           por_instrumento=r['inst'][0].get('instrumentos', []),
                           perfiles_por_instrumento=r['perf_inst'][0].get('instrumentos', []),
                           seg_genero=r['seg_genero'][0].get('conteo', []),
                           seg_genero_perfiles=r['seg_genero'][0].get('segmentacion', []),
                           seg_edad=r['seg_edad'][0].get('conteo', []),
                           seg_edad_perfiles=r['seg_edad'][0].get('segmentacion', []))


@admin_bp.route('/usuarios')
@admin_required
@solo_gestion
def usuarios():
    """Gestión de usuarios."""
    page = request.args.get('page', 1, type=int)
    rol = request.args.get('rol')
    buscar = request.args.get('buscar', '').strip()

    params = {'page': page, 'per_page': 20}
    if rol:
        params['rol'] = rol
    if buscar:
        params['buscar'] = buscar

    data, status = api_request('GET', '/usuarios/', params=params)
    if status != 200:
        flash('Error al cargar usuarios', 'error')
        data = {'usuarios': [], 'total': 0, 'paginas': 0}

    roles_data, _ = api_request('GET', '/usuarios/roles')
    roles = roles_data.get('roles', [])

    return render_template('admin/usuarios.html',
                           usuarios=data.get('usuarios', []),
                           total=data.get('total', 0),
                           paginas=data.get('paginas', 0),
                           pagina_actual=page,
                           rol_filtro=rol,
                           buscar=buscar,
                           roles=roles)


@admin_bp.route('/usuarios/<int:id>/toggle-activo', methods=['POST'])
@admin_required
@solo_gestion
def toggle_activo_usuario(id):
    """Activar o desactivar un usuario."""
    from flask import jsonify as flask_jsonify
    data, status = api_request('GET', f'/usuarios/{id}')
    if status != 200:
        return flask_jsonify({'error': 'Usuario no encontrado'}), 404
    activo_actual = data.get('usuario', {}).get('activo', True)
    upd, upd_status = api_request('PUT', f'/usuarios/{id}', {'activo': not activo_actual})
    if upd_status == 200:
        return flask_jsonify({'activo': not activo_actual}), 200
    return flask_jsonify({'error': upd.get('error', 'Error al actualizar')}), upd_status


@admin_bp.route('/usuarios/crear', methods=['POST'])
@admin_required
@solo_gestion
def crear_usuario():
    """Crear un nuevo usuario desde el panel admin."""
    datos = {
        'nombres': request.form.get('nombres', '').strip(),
        'apellidos': request.form.get('apellidos', '').strip(),
        'email': request.form.get('email', '').strip(),
        'password': request.form.get('password', ''),
        'rol': request.form.get('rol', 'estudiante'),
        'activo': request.form.get('activo', 'true') == 'true',
    }
    data, status = api_request('POST', '/usuarios/', datos)
    if status == 201:
        flash('Usuario creado exitosamente.', 'success')
    else:
        flash(data.get('error', 'Error al crear el usuario'), 'error')
    return redirect(url_for('admin.usuarios'))


@admin_bp.route('/usuarios/<int:id>/editar', methods=['POST'])
@admin_required
@solo_gestion
def editar_usuario(id):
    """Editar datos de un usuario."""
    datos = {}
    for campo in ('nombres', 'apellidos', 'email', 'rol'):
        val = request.form.get(campo, '').strip()
        if val:
            datos[campo] = val
    activo_val = request.form.get('activo')
    if activo_val is not None:
        datos['activo'] = activo_val == 'true'

    data, status = api_request('PUT', f'/usuarios/{id}', datos)
    if status == 200:
        flash('Usuario actualizado correctamente.', 'success')
    else:
        flash(data.get('error', 'Error al actualizar el usuario'), 'error')
    return redirect(url_for('admin.usuarios'))


@admin_bp.route('/instrumento')
@admin_required
@solo_gestion
def instrumento():
    """Configuración del instrumento psicométrico."""
    # Lista de instrumentos y configuraciones en paralelo
    init_r = api_requests_parallel([
        ('lista',  'GET', '/instrumentos/'),
        ('config', 'GET', '/configuracion/'),
    ])
    instrumentos_basicos = init_r['lista'][0].get('instrumentos', [])
    configuraciones = init_r['config'][0].get('configuraciones', [])

    # Detalles de cada instrumento en paralelo (elimina N+1)
    if instrumentos_basicos:
        detail_r = api_requests_parallel([
            (str(inst['id']), 'GET', f'/instrumentos/{inst["id"]}')
            for inst in instrumentos_basicos
        ])
        instrumentos = [
            detail_r[str(inst['id'])][0].get('instrumento', inst)
            for inst in instrumentos_basicos
        ]
    else:
        instrumentos = []

    return render_template('admin/instrumento.html',
                           instrumentos=instrumentos,
                           configuraciones=configuraciones)


@admin_bp.route('/instrumento/crear', methods=['POST'])
@admin_required
@solo_gestion
def crear_instrumento():
    """Crear un nuevo instrumento psicométrico."""
    datos = {
        'nombre': request.form.get('nombre', '').strip(),
        'descripcion': request.form.get('descripcion', '').strip(),
        'version': request.form.get('version', '1.0').strip(),
    }
    data, status = api_request('POST', '/instrumentos/', datos)
    if status == 201:
        flash('Instrumento creado exitosamente.', 'success')
        nuevo_id = data.get('instrumento', {}).get('id')
        if nuevo_id:
            return redirect(url_for('admin.detalle_instrumento', id=nuevo_id))
    else:
        flash(data.get('error', 'Error al crear el instrumento'), 'error')
    return redirect(url_for('admin.instrumento'))


@admin_bp.route('/instrumento/<int:inst_id>/dimensiones/crear', methods=['POST'])
@admin_required
@solo_gestion
def crear_dimension(inst_id):
    """Crear una dimensión en un instrumento."""
    datos = {
        'nombre': request.form.get('nombre', '').strip(),
        'descripcion': request.form.get('descripcion', '').strip(),
        'orden': request.form.get('orden', 0, type=int),
        'peso': request.form.get('peso', 1.0, type=float),
    }
    data, status = api_request('POST', f'/instrumentos/{inst_id}/dimensiones', datos)
    if status == 201:
        flash('Dimensión creada exitosamente.', 'success')
    else:
        flash(data.get('error', 'Error al crear la dimensión'), 'error')
    return redirect(url_for('admin.detalle_instrumento', id=inst_id))


@admin_bp.route('/dimensiones/<int:dim_id>/escalas/crear', methods=['POST'])
@admin_required
@solo_gestion
def crear_escala(dim_id):
    """Crear una escala en una dimensión."""
    datos = {
        'nombre': request.form.get('nombre', '').strip(),
        'descripcion': request.form.get('descripcion', '').strip(),
        'orden': request.form.get('orden', 0, type=int),
    }
    data, status = api_request('POST', f'/instrumentos/dimensiones/{dim_id}/escalas', datos)
    inst_id = request.form.get('instrumento_id', type=int)
    if status == 201:
        flash('Escala creada exitosamente.', 'success')
    else:
        flash(data.get('error', 'Error al crear la escala'), 'error')
    if inst_id:
        return redirect(url_for('admin.detalle_instrumento', id=inst_id))
    return redirect(url_for('admin.instrumento'))


@admin_bp.route('/configuraciones/<int:id>/toggle-activa', methods=['POST'])
@admin_required
@solo_gestion
def toggle_activa_configuracion(id):
    """Activar o desactivar una configuración de aplicación."""
    from flask import jsonify as flask_jsonify
    # Obtener estado actual
    data, status = api_request('GET', f'/configuracion/{id}')
    if status != 200:
        return flask_jsonify({'error': 'Configuración no encontrada'}), 404
    activa_actual = data.get('configuracion', {}).get('activa', False)
    # Invertir
    upd, upd_status = api_request('PUT', f'/configuracion/{id}', {'activa': not activa_actual})
    if upd_status == 200:
        return flask_jsonify({'activa': not activa_actual}), 200
    return flask_jsonify({'error': upd.get('error', 'Error al actualizar')}), upd_status


@admin_bp.route('/instrumento/<int:id>')
@admin_required
@solo_gestion
def detalle_instrumento(id):
    """Ver detalle de instrumento con dimensiones, escalas e ítems."""
    data, _ = api_request('GET', f'/instrumentos/{id}')
    instrumento = data.get('instrumento', {})
    return render_template('admin/detalle_instrumento.html', instrumento=instrumento)


# ── Banco de preguntas ────────────────────────────────────────────────────────

@admin_bp.route('/banco-preguntas')
@admin_required
@solo_gestion
def banco_preguntas():
    """Banco de preguntas: listar, buscar y filtrar ítems."""
    buscar = request.args.get('buscar', '')
    instrumento_id = request.args.get('instrumento_id', '', type=str)
    area = request.args.get('area', '')

    params = {}
    if buscar:
        params['buscar'] = buscar
    if instrumento_id:
        params['instrumento_id'] = instrumento_id
    if area:
        params['area'] = area

    items_r, _ = api_request('GET', '/instrumentos/items', params=params)
    insts_r, _ = api_request('GET', '/instrumentos/')

    # Recopilar escalas de todos los instrumentos para el formulario de creación
    escalas = []
    for inst in insts_r.get('instrumentos', []):
        det, _ = api_request('GET', f'/instrumentos/{inst["id"]}')
        for dim in det.get('instrumento', {}).get('dimensiones', []):
            for esc in dim.get('escalas', []):
                escalas.append({
                    'id': esc['id'],
                    'label': f'{inst["nombre"][:25]} › {dim["nombre"][:20]} › {esc["nombre"]}',
                    'instrumento': inst['nombre'],
                    'area': esc['nombre'],
                })

    areas = ['Realista', 'Investigador', 'Artístico', 'Social', 'Emprendedor', 'Convencional']

    return render_template('admin/banco_preguntas.html',
                           items=items_r.get('items', []),
                           total=items_r.get('total', 0),
                           instrumentos=insts_r.get('instrumentos', []),
                           escalas=escalas,
                           areas=areas,
                           buscar=buscar,
                           filtro_instrumento=instrumento_id,
                           filtro_area=area)


@admin_bp.route('/banco-preguntas/crear', methods=['POST'])
@admin_required
@solo_gestion
def crear_pregunta():
    """Crear un nuevo ítem en una escala."""
    escala_id = request.form.get('escala_id', type=int)
    datos = {
        'texto': request.form.get('texto', '').strip(),
        'tipo': request.form.get('tipo', 'eleccion_forzada'),
        'obligatorio': True,
        'orden': request.form.get('orden', 0, type=int),
    }
    api_request('POST', f'/instrumentos/escalas/{escala_id}/items', data=datos)
    flash('Pregunta creada correctamente.', 'success')
    return redirect(request.referrer or url_for('admin.banco_preguntas'))


@admin_bp.route('/banco-preguntas/<int:item_id>/editar', methods=['POST'])
@admin_required
@solo_gestion
def editar_pregunta(item_id):
    """Editar el enunciado y las respuestas de un ítem."""
    datos = {'texto': request.form.get('texto', '').strip()}
    tipo = request.form.get('tipo', '')

    if tipo == 'comparacion_binaria':
        datos['opciones'] = {
            'opcion_a': {
                'campo': request.form.get('campo_a', '').strip(),
                'texto': request.form.get('opcion_a', '').strip(),
            },
            'opcion_b': {
                'campo': request.form.get('campo_b', '').strip(),
                'texto': request.form.get('opcion_b', '').strip(),
            },
        }
    elif tipo == 'juicio_situacional':
        opciones = []
        for letra in ('A', 'B', 'C', 'D'):
            puntaje = request.form.get(f'puntaje_{letra.lower()}', type=int)
            if puntaje not in (1, 2, 3, 4):
                flash('Cada respuesta debe tener un puntaje entre 1 y 4.', 'error')
                return redirect(request.referrer or url_for('admin.banco_preguntas'))
            opciones.append({
                'letra': letra,
                'texto': request.form.get(f'opcion_{letra.lower()}', '').strip(),
                'puntaje': puntaje,
            })
        datos['opciones'] = {'opciones': opciones}
    elif tipo == 'opcion_multiple':
        textos = request.form.getlist('opciones_multiple')
        datos['opciones'] = {'opciones': [
            {'texto': texto.strip(), 'valor': 0} for texto in textos if texto.strip()
        ]}
    api_request('PUT', f'/instrumentos/items/{item_id}', data=datos)
    flash('Pregunta actualizada.', 'success')
    return redirect(request.referrer or url_for('admin.banco_preguntas'))


@admin_bp.route('/banco-preguntas/<int:item_id>/toggle-activo', methods=['POST'])
@admin_required
@solo_gestion
def toggle_activo_pregunta(item_id):
    """Activar o desactivar una pregunta del banco de preguntas."""
    data, status = api_request('GET', f'/instrumentos/items')
    # Debemos buscar el item concreto en el listado de pruebas para detectar estado.
    item = None
    for pregunta in data.get('items', []):
        if pregunta.get('id') == item_id:
            item = pregunta
            break
    if not item:
        flash('Pregunta no encontrada.', 'error')
        return redirect(request.referrer or url_for('admin.banco_preguntas'))

    nuevo_estado = not bool(item.get('activo', True))
    upd, upd_status = api_request('PUT', f'/instrumentos/items/{item_id}', {'activo': nuevo_estado})
    if upd_status == 200:
        flash('Estado de la pregunta actualizado.', 'success')
    else:
        flash(upd.get('error', 'No se pudo actualizar la pregunta'), 'error')
    return redirect(request.referrer or url_for('admin.banco_preguntas'))


@admin_bp.route('/banco-preguntas/<int:item_id>/eliminar', methods=['POST'])
@admin_required
@solo_gestion
def eliminar_pregunta(item_id):
    """Eliminar un ítem."""
    api_request('DELETE', f'/instrumentos/items/{item_id}')
    flash('Pregunta eliminada.', 'success')
    return redirect(request.referrer or url_for('admin.banco_preguntas'))


@admin_bp.route('/configuracion/nueva', methods=['GET', 'POST'])
@admin_required
@solo_gestion
def nueva_configuracion():
    """Crear nueva configuración de aplicación."""
    if request.method == 'POST':
        datos = {
            'instrumento_id': request.form.get('instrumento_id', type=int),
            'nombre': request.form.get('nombre'),
            'descripcion': request.form.get('descripcion'),
            'fecha_inicio': request.form.get('fecha_inicio'),
            'fecha_fin': request.form.get('fecha_fin'),
            'obligatoria': request.form.get('obligatoria') == 'on',
            'cohorte': request.form.get('cohorte'),
        }

        data, status = api_request('POST', '/configuracion/', datos)
        if status == 201:
            flash('Configuración creada exitosamente.', 'success')
            return redirect(url_for('admin.instrumento'))
        else:
            flash(data.get('error', 'Error al crear configuración'), 'error')

    data, _ = api_request('GET', '/instrumentos/')
    instrumentos = data.get('instrumentos', [])
    return render_template('admin/nueva_configuracion.html', instrumentos=instrumentos)


@admin_bp.route('/consultas')
@admin_required
@solo_gestion
def consultas():
    """Consulta de resultados individuales."""
    page    = request.args.get('page', 1, type=int)
    buscar  = request.args.get('buscar', '').strip()
    perfil  = request.args.get('perfil', '').strip()

    params = {'page': page, 'per_page': 20}
    if buscar:
        params['buscar'] = buscar
    if perfil:
        params['perfil'] = perfil

    data, _ = api_request('GET', '/consultas/buscar', params=params)

    return render_template('admin/consultas.html',
                           resultados=data.get('resultados', []),
                           total=data.get('total', 0),
                           paginas=data.get('paginas', 0),
                           pagina_actual=page,
                           buscar=buscar,
                           perfil_filtro=perfil)



# Nueva ruta para Estadísticas Agregadas
@admin_bp.route('/estadisticas-agregadas')
@admin_required
def estadisticas_agregadas():
    """Vista de estadísticas agregadas según el rol."""
    return render_template('admin/estadisticas_agregadas.html')


@admin_bp.route('/exportar')
@admin_required
def exportar():
    """Página de exportación de datos con gráfica de evolución agregada."""
    evol_r, _ = api_request('GET', '/estadisticas/evolucion-agregada')
    return render_template('admin/exportar.html',
                           evolucion_agregada=evol_r.get('evolucion', []))


@admin_bp.route('/evolucion-estudiantes')
@admin_required
def evolucion_estudiantes():
    """Dashboard de evolución vocacional de estudiantes (vista asesor/orientador)."""
    page = request.args.get('page', 1, type=int)
    buscar = request.args.get('buscar', '').strip()

    params = {'page': page, 'per_page': 20}
    if buscar:
        params['buscar'] = buscar

    data, status = api_request('GET', '/estadisticas/resumen-estudiantes', params=params)
    if status != 200:
        flash('Error al cargar la evolución de estudiantes.', 'error')
        data = {'estudiantes': [], 'total': 0, 'paginas': 0}

    return render_template('admin/evolucion_estudiantes.html',
                           estudiantes=data.get('estudiantes', []),
                           total=data.get('total', 0),
                           paginas=data.get('paginas', 0),
                           pagina_actual=page,
                           buscar=buscar)


@admin_bp.route('/api/evolucion-estudiante/<int:usuario_id>')
@admin_required
def api_evolucion_estudiante(usuario_id):
    """Proxy JSON: devuelve evolución vocacional de un estudiante para AJAX."""
    from flask import jsonify as flask_json
    data, status = api_request('GET', f'/estadisticas/evolucion/{usuario_id}')
    return flask_json(data), status


@admin_bp.route('/resultados-estudiante/<int:usuario_id>')
@admin_required
def resultados_estudiante_admin(usuario_id):
    """Redirige al resultado más reciente de un estudiante."""
    # 1. Obtener todas las aplicaciones del estudiante
    data, status = api_request('GET', f'/consultas/estudiante/{usuario_id}')
    if status != 200:
        flash('Estudiante no encontrado.', 'error')
        return redirect(url_for('admin.consultas'))

    aplicaciones = data.get('aplicaciones', [])
    # Buscar la última aplicación completada
    ultima_completada = None
    for app in aplicaciones:
        if app.get('aplicacion', {}).get('estado') == 'completada':
            ultima_completada = app.get('aplicacion', {})
            break

    if not ultima_completada:
        flash('El estudiante aún no tiene pruebas completadas.', 'info')
        return redirect(url_for('admin.consultas'))

    aplicacion_id = ultima_completada.get('id')
    return redirect(url_for('estudiante.resultados', aplicacion_id=aplicacion_id))



@admin_bp.route('/exportar/csv/resultados')
@admin_required
def exportar_csv_resultados():
    """Proxy: descarga CSV de resultados (anonimizado o identificado) con JWT."""
    anonimizado = request.args.get('anonimizado', 'true')
    resp = api_request_file('GET', '/exportacion/csv/resultados',
                            params={'anonimizado': anonimizado})
    if resp is None or resp.status_code != 200:
        flash('Error al generar el CSV. Verifique permisos e inténtelo de nuevo.', 'error')
        return redirect(url_for('admin.exportar'))
    return FlaskResponse(
        resp.content,
        status=200,
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': resp.headers.get(
            'Content-Disposition', 'attachment; filename=resultados.csv')},
    )


@admin_bp.route('/exportar/csv/estadisticas')
@admin_required
def exportar_csv_estadisticas():
    """Proxy: descarga CSV de estadísticas agregadas con JWT."""
    resp = api_request_file('GET', '/exportacion/csv/estadisticas')
    if resp is None or resp.status_code != 200:
        flash('Error al generar el CSV de estadísticas.', 'error')
        return redirect(url_for('admin.exportar'))
    return FlaskResponse(
        resp.content,
        status=200,
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': resp.headers.get(
            'Content-Disposition', 'attachment; filename=estadisticas.csv')},
    )


@admin_bp.route('/exportar/excel/completo')
@admin_required
def exportar_excel_completo():
    """Proxy: descarga el Excel completo (identificación, aplicación, respuestas,
    intereses, competencias y perfil integrado) con JWT."""
    resp = api_request_file('GET', '/exportacion/excel/completo')
    if resp is None or resp.status_code != 200:
        flash('Error al generar el Excel. Verifique permisos e inténtelo de nuevo.', 'error')
        return redirect(url_for('admin.exportar'))
    return FlaskResponse(
        resp.content,
        status=200,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': resp.headers.get(
            'Content-Disposition', 'attachment; filename=orientacion_vocacional_simulacion.xlsx')},
    )


@admin_bp.route('/auditoria')
@admin_required
@solo_gestion
def auditoria():
    """Logs de auditoría."""
    page = request.args.get('page', 1, type=int)
    modulo = request.args.get('modulo', '').strip()
    accion = request.args.get('accion', '').strip()
    usuario_nombre = request.args.get('usuario_nombre', '').strip()

    params = {'page': page, 'per_page': 50}
    if modulo:
        params['modulo'] = modulo
    if accion:
        params['accion'] = accion
    if usuario_nombre:
        params['usuario_nombre'] = usuario_nombre

    data, _ = api_request('GET', '/auditoria/logs', params=params)
    politicas_data, _ = api_request('GET', '/auditoria/politicas')

    return render_template('admin/auditoria.html',
                           logs=data.get('logs', []),
                           total=data.get('total', 0),
                           paginas=data.get('paginas', 0),
                           pagina_actual=page,
                           filtro_modulo=modulo,
                           filtro_accion=accion,
                           filtro_usuario_nombre=usuario_nombre,
                           politicas=politicas_data.get('politicas', []),
                           solo_estudiantes=False)


@admin_bp.route('/auditoria-estudiantes')
@admin_required
@solo_gestion
def auditoria_estudiantes():
    """Auditoría filtrada a acciones de estudiantes (para bienestar)."""
    page = request.args.get('page', 1, type=int)
    usuario_nombre = request.args.get('usuario_nombre', '').strip()
    accion = request.args.get('accion', '').strip()

    params = {'page': page, 'per_page': 50, 'rol_usuario': 'estudiante'}
    if usuario_nombre:
        params['usuario_nombre'] = usuario_nombre
    if accion:
        params['accion'] = accion

    data, _ = api_request('GET', '/auditoria/logs', params=params)

    return render_template('admin/auditoria.html',
                           logs=data.get('logs', []),
                           total=data.get('total', 0),
                           paginas=data.get('paginas', 0),
                           pagina_actual=page,
                           filtro_modulo='',
                           filtro_accion=accion,
                           filtro_usuario_nombre=usuario_nombre,
                           politicas=[],
                           solo_estudiantes=True)


@admin_bp.route('/auditoria/politicas/crear', methods=['POST'])
@admin_required
@solo_gestion
def crear_politica_retencion():
    """Crear una política de retención de datos."""
    datos = {
        'nombre': request.form.get('nombre', '').strip(),
        'descripcion': request.form.get('descripcion', '').strip(),
        'tiempo_retencion_dias': request.form.get('tiempo_retencion_dias', type=int, default=365),
        'tabla_afectada': request.form.get('tabla_afectada', '').strip(),
    }
    data, status = api_request('POST', '/auditoria/politicas', datos)
    if status == 201:
        flash('Política de retención creada.', 'success')
    else:
        flash(data.get('error', 'Error al crear la política'), 'error')
    return redirect(url_for('admin.auditoria'))


def _aplanar_perfiles_colegio(nested):
    """Convierte [{tipo_colegio, perfiles:[{perfil, cantidad}]}] en lista plana."""
    plana = []
    for grupo in nested:
        for p in grupo.get('perfiles', []):
            plana.append({
                'tipo_colegio': grupo.get('tipo_colegio', ''),
                'perfil': p.get('perfil', ''),
                'cantidad': p.get('cantidad', 0),
            })
    return plana


@admin_bp.route('/informe-general')
@admin_required
def informe_general():
    """Informe general — estadísticas por colegio, comparativas, distribución por áreas."""
    r = api_requests_parallel([
        ('tipo_colegio',     'GET', '/estadisticas/por-tipo-colegio'),
        ('perfiles_colegio', 'GET', '/estadisticas/perfiles-por-colegio'),
        ('areas',            'GET', '/estadisticas/areas-interes'),
        ('perfiles',         'GET', '/estadisticas/perfiles'),
        ('resumen',          'GET', '/estadisticas/resumen'),
        ('seg_genero',       'GET', '/estadisticas/segmentacion/genero'),
        ('seg_edad',         'GET', '/estadisticas/segmentacion/edad'),
        ('evolucion',        'GET', '/estadisticas/evolucion-agregada'),
    ])

    rol = session.get('rol', '')
    return render_template('admin/informe_general.html',
                           tipo_colegio=r['tipo_colegio'][0].get('tipo_colegio', []),
                           perfiles_colegio=_aplanar_perfiles_colegio(r['perfiles_colegio'][0].get('distribucion', [])),
                           areas_interes=r['areas'][0].get('distribucion', []),
                           perfiles=r['perfiles'][0].get('distribucion', []),
                           resumen=r['resumen'][0],
                           seg_genero=r['seg_genero'][0].get('conteo', []),
                           seg_genero_perfiles=r['seg_genero'][0].get('segmentacion', []),
                           seg_edad=r['seg_edad'][0].get('conteo', []),
                           seg_edad_perfiles=r['seg_edad'][0].get('segmentacion', []),
                           evolucion_agregada=r['evolucion'][0].get('evolucion', []),
                           rol=rol)


@admin_bp.route('/campos-demograficos', methods=['GET'])
@admin_required
@solo_gestion
def campos_demograficos():
    """Gestión de campos demográficos configurables."""
    data, _ = api_request('GET', '/demografico/campos', params={'activos': 'false'})
    campos = data.get('campos', [])
    return render_template('admin/campos_demograficos.html', campos=campos)


@admin_bp.route('/datos-estudiantes')
@admin_required
@solo_gestion
def datos_estudiantes():
    """Ver datos demográficos de todos los estudiantes."""
    page = request.args.get('page', 1, type=int)
    buscar = request.args.get('buscar', '')

    params = {'page': page, 'per_page': 20}
    if buscar:
        params['buscar'] = buscar

    data, status = api_request('GET', '/demografico/datos/todos', params=params)

    return render_template('admin/datos_estudiantes.html',
                           estudiantes=data.get('estudiantes', []),
                           campos=data.get('campos', []),
                           total=data.get('total', 0),
                           paginas=data.get('paginas', 0),
                           pagina_actual=page,
                           buscar=buscar)


@admin_bp.route('/campos-demograficos/crear', methods=['POST'])
@admin_required
def crear_campo_demografico():
    """Crear un nuevo campo demográfico."""
    datos = {
        'nombre': request.form.get('nombre'),
        'etiqueta': request.form.get('etiqueta'),
        'tipo_campo': request.form.get('tipo_campo', 'texto'),
        'obligatorio': request.form.get('obligatorio') == 'on',
        'orden': request.form.get('orden', 0, type=int),
    }

    opciones_raw = request.form.get('opciones', '').strip()
    if opciones_raw and datos['tipo_campo'] in ('seleccion', 'seleccion_multiple'):
        datos['opciones'] = [o.strip() for o in opciones_raw.split(',') if o.strip()]

    data, status = api_request('POST', '/demografico/campos', datos)
    if status == 201:
        flash('Campo demográfico creado exitosamente.', 'success')
    else:
        flash(data.get('error', 'Error al crear el campo'), 'error')

    return redirect(url_for('admin.campos_demograficos'))


@admin_bp.route('/campos-demograficos/<int:id>/toggle', methods=['POST'])
@admin_required
def toggle_campo_demografico(id):
    """Activar/desactivar un campo demográfico."""
    activo = request.form.get('activo') == 'true'
    data, status = api_request('PUT', f'/demografico/campos/{id}', {'activo': activo})
    if status == 200:
        flash('Campo actualizado.', 'success')
    else:
        flash('Error al actualizar el campo.', 'error')
    return redirect(url_for('admin.campos_demograficos'))


# ── Fórmulas de Cálculo (configuración de ítems) ──────────────────────────── #

@admin_bp.route('/formulas-calculo')
@admin_required
@solo_gestion
def formulas_calculo():
    """Gestión de fórmulas de cálculo para los ítems de las pruebas."""
    data, _ = api_request('GET', '/demografico/formulas')
    formulas = data.get('formulas', [])
    return render_template('admin/formulas_calculo.html', formulas=formulas)


# ── Módulos ML / PLN ───────────────────────────────────────────────────────── #

@admin_bp.route('/ml-pln')
@admin_required
def ml_dashboard():
    """Panel de módulos ML / PLN: Clustering y Procesamiento de Lenguaje Natural."""
    r = api_requests_parallel([
        ('configs',       'GET', '/configuracion/'),
        ('instrumentos',  'GET', '/instrumentos/'),
    ])
    configuraciones = r['configs'][0].get('configuraciones', [])
    instrumentos = r['instrumentos'][0].get('instrumentos', [])
    return render_template('admin/ml_dashboard.html',
                           configuraciones=configuraciones,
                           instrumentos=instrumentos)


# ── Proxies AJAX para el dashboard ML (evitan llamadas directas browser→backend) ──

@admin_bp.route('/api/ml/resumen')
@admin_required
def api_ml_resumen():
    from flask import jsonify as _j
    data, status = api_request('GET', '/ml/resumen')
    return _j(data), status

@admin_bp.route('/api/ml/clustering/ejecutar', methods=['POST'])
@admin_required
def api_ml_clustering_ejecutar():
    from flask import jsonify as _j
    body = request.get_json() or {}
    data, status = api_request('POST', '/ml/clustering/ejecutar', body)
    return _j(data), status

@admin_bp.route('/api/ml/clustering/combinaciones')
@admin_required
def api_ml_clustering_combinaciones():
    from flask import jsonify as _j
    data, status = api_request('GET', '/ml/clustering/combinaciones')
    return _j(data), status

@admin_bp.route('/api/ml/clustering/historial')
@admin_required
def api_ml_clustering_historial():
    from flask import jsonify as _j
    data, status = api_request('GET', '/ml/clustering/historial')
    return _j(data), status

@admin_bp.route('/api/ml/clustering/<int:resultado_id>')
@admin_required
def api_ml_clustering_detalle(resultado_id):
    from flask import jsonify as _j
    data, status = api_request('GET', f'/ml/clustering/{resultado_id}')
    return _j(data), status

@admin_bp.route('/api/ml/pln/analizar-texto', methods=['POST'])
@admin_required
def api_ml_pln_analizar():
    from flask import jsonify as _j
    body = request.get_json() or {}
    data, status = api_request('POST', '/ml/pln/analizar-texto', body)
    return _j(data), status


@admin_bp.route('/formulas-calculo/crear', methods=['POST'])
@admin_required
@solo_gestion
def crear_formula():
    """Crear una nueva fórmula de cálculo (json, codigo o csv)."""
    import json as _json
    formato = request.form.get('formato', 'json')
    parametros = _construir_parametros(formato, request.form)
    if parametros is None:
        return redirect(url_for('admin.formulas_calculo'))

    datos = {
        'nombre': request.form.get('nombre'),
        'descripcion': request.form.get('descripcion', ''),
        'tipo': request.form.get('tipo', 'holland_riasec'),
        'parametros': parametros,
    }
    data, status = api_request('POST', '/demografico/formulas', datos)
    if status == 201:
        flash('Fórmula creada exitosamente.', 'success')
    else:
        flash(data.get('error', 'Error al crear la fórmula'), 'error')
    return redirect(url_for('admin.formulas_calculo'))


@admin_bp.route('/formulas-calculo/<int:id>/activar', methods=['POST'])
@admin_required
def activar_formula(id):
    """Activar una fórmula (desactiva las otras automáticamente en el servicio)."""
    data, status = api_request('PUT', f'/demografico/formulas/{id}', {'activa': True})
    if status == 200:
        flash('Fórmula activada. Los nuevos cálculos usarán esta fórmula.', 'success')
    else:
        flash(data.get('error', 'Error al activar la fórmula'), 'error')
    return redirect(url_for('admin.formulas_calculo'))


@admin_bp.route('/formulas-calculo/<int:id>/editar', methods=['POST'])
@admin_required
@solo_gestion
def editar_formula(id):
    """Editar parámetros de una fórmula de cálculo (json, codigo o csv)."""
    formato = request.form.get('formato', 'json')
    parametros = _construir_parametros(formato, request.form)
    if parametros is None:
        return redirect(url_for('admin.formulas_calculo'))

    datos = {
        'nombre': request.form.get('nombre'),
        'descripcion': request.form.get('descripcion', ''),
        'parametros': parametros,
    }
    data, status = api_request('PUT', f'/demografico/formulas/{id}', datos)
    if status == 200:
        flash('Fórmula actualizada.', 'success')
    else:
        flash(data.get('error', 'Error al actualizar'), 'error')
    return redirect(url_for('admin.formulas_calculo'))


def _construir_parametros(formato, form):
    """Construye el dict de parametros según el formato seleccionado."""
    import json as _json
    if formato == 'codigo':
        codigo = form.get('codigo_contenido', '').strip()
        if not codigo:
            flash('El contenido del código no puede estar vacío.', 'error')
            return None
        return {'_formato': 'codigo', '_codigo': codigo}
    elif formato == 'csv':
        csv_raw = form.get('csv_contenido', '').strip()
        if not csv_raw:
            flash('El contenido CSV no puede estar vacío.', 'error')
            return None
        # Parsear CSV para validarlo y guardar filas estructuradas
        import io, csv as _csv
        filas = []
        try:
            reader = _csv.DictReader(io.StringIO(csv_raw))
            for row in reader:
                filas.append(dict(row))
        except Exception:
            flash('El CSV no pudo ser parseado. Revise el formato.', 'error')
            return None
        return {'_formato': 'csv', '_csv': csv_raw, '_filas': filas}
    else:  # json
        raw = form.get('parametros', '{}').strip()
        try:
            params = _json.loads(raw)
            params['_formato'] = 'json'
            return params
        except ValueError:
            flash('Los parámetros deben estar en formato JSON válido.', 'error')
            return None
