"""Rutas del estudiante — inicio, formulario demográfico, cuestionario, resultados."""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from ..utils import api_request, api_requests_parallel, api_request_file, jwt_is_expired

estudiante_routes = Blueprint('estudiante', __name__)


def login_required(f):
    """Decorador para requerir login en el frontend. Verifica expiración localmente."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        token = session.get('access_token')
        if not token:
            flash('Debes iniciar sesión para acceder.', 'warning')
            return redirect(url_for('auth.login'))
        if jwt_is_expired(token):
            session.clear()
            flash('Tu sesión ha expirado. Por favor inicia sesión nuevamente.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@estudiante_routes.route('/inicio')
@login_required
def inicio():
    """Dashboard del estudiante."""
    r = api_requests_parallel([
        ('mis_apps',   'GET', '/aplicaciones/mis-aplicaciones'),
        ('disponibles','GET', '/aplicaciones/disponibles'),
        ('demo',       'GET', '/demografico/datos/completo'),
    ])

    aplicaciones = r['mis_apps'][0].get('aplicaciones', [])       if r['mis_apps'][1]    == 200 else []
    disponibles  = r['disponibles'][0].get('configuraciones', []) if r['disponibles'][1] == 200 else []
    datos_completos = r['demo'][0].get('completo', False) if r['demo'][0] else False

    # Construir 3 tarjetas unificadas: una por config disponible con estado real del estudiante
    # Para cada config, buscar la aplicación más reciente del estudiante en esa config
    apps_por_config = {}
    for app in aplicaciones:
        cid = app.get('configuracion_id')
        if cid not in apps_por_config:
            apps_por_config[cid] = app  # ya vienen ordenadas desc por fecha

    prueba_cards = []
    for config in disponibles:
        cid = config.get('id')
        app = apps_por_config.get(cid)  # última app para esta config, o None
        prueba_cards.append({
            'config': config,
            'app': app,
            'estado': app.get('estado') if app else 'no_iniciada',
        })

    # Historial: mostrar aplicaciones pasadas para no ocultar resultados anteriores
    # Filtramos las abandonadas para no saturar, pero si solo hay abandonadas, las mostramos.
    apps_validas = [app for app in aplicaciones if app.get('estado') != 'abandonada']
    if apps_validas:
        historial = apps_validas[:10]
    else:
        historial = aplicaciones[:5]

    return render_template('estudiante/inicio.html',
                           prueba_cards=prueba_cards,
                           historial=historial,
                           datos_demograficos_completos=datos_completos)


@estudiante_routes.route('/datos-demograficos', methods=['GET', 'POST'])
@login_required
def datos_demograficos():
    """Formulario demográfico configurable."""
    if request.method == 'POST':
        datos = request.get_json() if request.is_json else None

        if datos:
            # Petición AJAX
            data, status = api_request('POST', '/demografico/datos', datos)
            return jsonify(data), status
        else:
            # Formulario tradicional
            campos_data, _ = api_request('GET', '/demografico/campos')
            campos = campos_data.get('campos', [])

            respuestas = []
            for campo in campos:
                valor = request.form.get(f'campo_{campo["id"]}', '').strip()
                if valor:
                    respuestas.append({'campo_id': campo['id'], 'valor': valor})

            data, status = api_request('POST', '/demografico/datos', {'respuestas': respuestas})

            if status == 200:
                flash('Datos demográficos guardados correctamente.', 'success')
                redirect_to = request.args.get('next')
                if redirect_to:
                    return redirect(redirect_to)
                return redirect(url_for('estudiante.inicio'))
            else:
                flash(data.get('error', 'Error al guardar los datos'), 'error')

    # GET: Obtener campos y datos existentes
    campos_data, _ = api_request('GET', '/demografico/campos')
    campos = campos_data.get('campos', [])

    datos_data, _ = api_request('GET', '/demografico/datos')
    datos_existentes = {d['campo_id']: d['valor'] for d in datos_data.get('datos', [])}

    return render_template('estudiante/datos_demograficos.html',
                           campos=campos,
                           datos_existentes=datos_existentes)


@estudiante_routes.route('/cuestionario/<int:config_id>')
@login_required
def cuestionario(config_id):
    """Página del cuestionario psicométrico."""
    # Verificar consentimiento y datos demográficos en paralelo
    checks = api_requests_parallel([
        ('consentimiento', 'GET', '/consentimiento/estado'),
        ('demo',           'GET', '/demografico/datos/completo'),
    ])

    if not checks['consentimiento'][0].get('tiene_consentimiento'):
        return redirect(url_for('auth.consentimiento'))

    if not checks['demo'][0].get('completo', False):
        flash('Debes completar tus datos demográficos antes de iniciar la prueba.', 'warning')
        return redirect(url_for('estudiante.datos_demograficos',
                                next=url_for('estudiante.cuestionario', config_id=config_id)))

    # Iniciar o continuar aplicación
    data, status = api_request('POST', '/aplicaciones/iniciar', {'configuracion_id': config_id})

    if status not in (200, 201):
        flash(data.get('error', 'No se pudo iniciar la prueba'), 'error')
        return redirect(url_for('estudiante.inicio'))

    aplicacion_id = data['aplicacion']['id']

    # Obtener configuración y progreso en paralelo
    r = api_requests_parallel([
        ('config',  'GET', f'/configuracion/{config_id}'),
        ('progreso','GET', f'/aplicaciones/{aplicacion_id}/progreso'),
    ])

    instrumento_id = r['config'][0].get('configuracion', {}).get('instrumento_id', 1)
    respuestas_previas = {
        item['item_id']: item['valor']
        for item in r['progreso'][0].get('respuestas', [])
    }

    # Obtener instrumento (depende de instrumento_id obtenido arriba)
    data_inst, _ = api_request('GET', f'/instrumentos/{instrumento_id}')
    instrumento = data_inst.get('instrumento', {})

    return render_template('estudiante/cuestionario.html',
                           instrumento=instrumento,
                           aplicacion_id=aplicacion_id,
                           config_id=config_id,
                           respuestas_previas=respuestas_previas)


@estudiante_routes.route('/guardar-respuestas', methods=['POST'])
@login_required
def guardar_respuestas():
    """Endpoint AJAX para guardar respuestas progresivamente."""
    datos = request.get_json()
    aplicacion_id = datos.get('aplicacion_id')
    respuestas = datos.get('respuestas', [])

    data, status = api_request('POST', f'/aplicaciones/{aplicacion_id}/respuestas', {
        'respuestas': respuestas
    })

    return jsonify(data), status


@estudiante_routes.route('/finalizar/<int:aplicacion_id>', methods=['POST'])
@login_required
def finalizar(aplicacion_id):
    """Finalizar la aplicación del instrumento."""
    # Finalizar aplicación
    data, status = api_request('POST', f'/aplicaciones/{aplicacion_id}/finalizar')

    if status != 200:
        flash(data.get('error', 'Error al finalizar'), 'error')
        return redirect(url_for('estudiante.inicio'))

    # Calcular resultados
    data_calc, _ = api_request('POST', f'/procesamiento/calcular/{aplicacion_id}')

    flash('¡Prueba completada exitosamente! Tus resultados están listos.', 'success')
    return redirect(url_for('estudiante.resultados', aplicacion_id=aplicacion_id))


def _unificar_puntajes_riasec(intereses_puntajes, competencias_puntajes, puntajes_area):
    """Unifica y calcula correctamente los puntajes brutos y normalizados combinados de ambas pruebas."""
    all_areas = set(list(intereses_puntajes.keys()) + list(competencias_puntajes.keys()) + list(puntajes_area.keys()))
    if not all_areas:
        all_areas = {'Realista', 'Investigador', 'Artístico', 'Social', 'Emprendedor', 'Convencional'}
        
    has_intereses = bool(intereses_puntajes)
    has_competencias = bool(competencias_puntajes)
    
    comparativo = {}
    for area in all_areas:
        comparativo[area] = {}
        
        # Intereses (Respuestas positivas y total posibles)
        int_val = (intereses_puntajes.get(area, {}).get('Intereses Vocacionales') or 
                   intereses_puntajes.get(area, {}).get('Intereses') or 
                   intereses_puntajes.get(area, {}).get('positivas') or 
                   intereses_puntajes.get(area, {}).get('bruto') or 0)
        comparativo[area]['Intereses Vocacionales'] = int_val
        int_max = intereses_puntajes.get(area, {}).get('total') or (5 if int_val <= 5 else 0)
        
        # Competencias (Respuestas positivas y total posibles)
        com_val = (competencias_puntajes.get(area, {}).get('Competencias Vocacionales') or 
                   competencias_puntajes.get(area, {}).get('Competencias') or 
                   competencias_puntajes.get(area, {}).get('positivas') or 
                   competencias_puntajes.get(area, {}).get('bruto') or 0)
        comparativo[area]['Competencias Vocacionales'] = com_val
        com_max = competencias_puntajes.get(area, {}).get('total') or (3 if com_val <= 3 else 0)
        
        # Determinar el máximo y puntaje según las pruebas que realmente existen
        if has_intereses and has_competencias:
            combined_max = int_max + com_max
            combined_score = int_val + com_val
        elif has_intereses:
            combined_max = int_max
            combined_score = int_val
        elif has_competencias:
            combined_max = com_max
            combined_score = com_val
        else:
            combined_max = (intereses_puntajes.get(area, {}).get('total') or 
                            competencias_puntajes.get(area, {}).get('total') or 
                            puntajes_area.get(area, {}).get('total') or 10)
            combined_score = int_val + com_val
            
        comparativo[area]['total'] = combined_max
        normalizado = (combined_score / combined_max * 100) if combined_max > 0 else 0
        comparativo[area]['normalizado'] = round(normalizado, 2)
        
    return comparativo


@estudiante_routes.route('/resultados/<int:aplicacion_id>')
@login_required
def resultados(aplicacion_id):
    """Página de resultados del estudiante."""

    r = api_requests_parallel([
        ('resultado',  'GET', f'/consultas/resultado/{aplicacion_id}'),
        ('evolucion',  'GET', '/estadisticas/evolucion/mi-evolucion'),  # Historial completo sin filtro
        ('mis_apps',   'GET', '/aplicaciones/mis-aplicaciones'),
    ])

    data, status = r['resultado']
    if status != 200:
        flash('No se pudieron cargar los resultados.', 'error')
        return redirect(url_for('estudiante.inicio'))

    evolucion_data = r['evolucion'][0] if r['evolucion'][1] == 200 else {}
    perfil = data.get('perfil') or {}
    puntajes_area = (perfil.get('datos_json') or {}).get('puntajes_por_area', {})
    app_config_id = (data.get('aplicacion') or {}).get('configuracion_id')
    mis_apps = r['mis_apps'][0].get('aplicaciones', []) if r['mis_apps'][1] == 200 else []

    # Determinar si la aplicación actual es de Intereses o Competencias
    current_app = data.get('aplicacion') or {}
    current_inst_name = (current_app.get('instrumento_nombre') or '').lower()

    intereses_app = None
    competencias_app = None

    if 'nteres' in current_inst_name:
        intereses_app = current_app
        # Buscar la competencia más reciente en mis_apps
        competencias_app = next((a for a in mis_apps if a.get('estado') == 'completada' and 'ompet' in (a.get('instrumento_nombre') or '').lower()), None)
    elif 'ompet' in current_inst_name:
        competencias_app = current_app
        # Buscar el interés más reciente en mis_apps
        intereses_app = next((a for a in mis_apps if a.get('estado') == 'completada' and 'nteres' in (a.get('instrumento_nombre') or '').lower()), None)
    else:
        # Fallback a los más recientes de cada uno si es otro tipo de instrumento
        intereses_app = next((a for a in mis_apps if a.get('estado') == 'completada' and 'nteres' in (a.get('instrumento_nombre') or '').lower()), None)
        competencias_app = next((a for a in mis_apps if a.get('estado') == 'completada' and 'ompet' in (a.get('instrumento_nombre') or '').lower()), None)


    intereses_puntajes = {}
    competencias_puntajes = {}
    if intereses_app:
        int_data, int_status = api_request('GET', f'/consultas/resultado/{intereses_app["id"]}')
        if int_status == 200:
            int_perfil = int_data.get('perfil') or {}
            intereses_puntajes = (int_perfil.get('datos_json') or {}).get('puntajes_por_area', {})
    if competencias_app:
        comp_data, comp_status = api_request('GET', f'/consultas/resultado/{competencias_app["id"]}')
        if comp_status == 200:
            comp_perfil = comp_data.get('perfil') or {}
            competencias_puntajes = (comp_perfil.get('datos_json') or {}).get('puntajes_por_area', {})

    # Unificar ambos puntajes en el perfil actual usando la función auxiliar
    comparativo = _unificar_puntajes_riasec(intereses_puntajes, competencias_puntajes, puntajes_area)

    # Sobrescribir puntajes_por_area para la tabla comparativa
    if perfil.get('datos_json'):
        perfil['datos_json']['puntajes_por_area'] = comparativo

    return render_template('estudiante/resultados.html',
                           perfil=perfil,
                           resultados_dimension=data.get('resultados_dimension', []),
                           aplicacion=data.get('aplicacion'),
                           estudiante=data.get('estudiante'),
                           evolucion=evolucion_data.get('evolucion', {}).get('historial', []),
                           mutaciones=evolucion_data.get('mutaciones', []),
                           prediccion=evolucion_data.get('prediccion', {}))


@estudiante_routes.route('/descargar-reporte/<int:aplicacion_id>')
@login_required
def descargar_reporte(aplicacion_id):
    """Genera el reporte PDF y lo sirve directamente al navegador (proxy con JWT)."""
    # 1. Solicitar generación del reporte
    data, status = api_request('POST', f'/reportes/generar/{aplicacion_id}')

    if status != 201:
        flash(data.get('error', 'Error al generar reporte'), 'error')
        return redirect(url_for('estudiante.resultados', aplicacion_id=aplicacion_id))

    reporte_id = data['reporte']['id']

    # 2. Descargar el PDF desde el backend usando el token JWT (proxy)
    resp = api_request_file('GET', f'/reportes/descargar/{reporte_id}')

    if resp is None or resp.status_code != 200:
        flash('No se pudo descargar el reporte. Intenta de nuevo.', 'error')
        return redirect(url_for('estudiante.resultados', aplicacion_id=aplicacion_id))

    from flask import Response as FlaskResponse
    filename = resp.headers.get('Content-Disposition', 'attachment; filename=reporte.pdf')
    return FlaskResponse(
        resp.content,
        status=200,
        mimetype='application/pdf',
        headers={'Content-Disposition': filename},
    )


@estudiante_routes.route('/explorador/<int:aplicacion_id>')
@login_required
def explorador(aplicacion_id):
    """Mapa Vocacional Interactivo — hexágono Holland con carreras colombianas."""
    r = api_requests_parallel([
        ('resultado',  'GET', f'/consultas/resultado/{aplicacion_id}'),
        ('mis_apps',   'GET', '/aplicaciones/mis-aplicaciones'),
    ])
    
    data, status = r['resultado']
    if status != 200:
        flash('No se pudieron cargar los resultados.', 'error')
        return redirect(url_for('estudiante.inicio'))

    perfil = data.get('perfil') or {}
    puntajes_area = (perfil.get('datos_json') or {}).get('puntajes_por_area', {})
    mis_apps = r['mis_apps'][0].get('aplicaciones', []) if r['mis_apps'][1] == 200 else []

    # Determinar si la aplicación actual es de Intereses o Competencias
    current_app = data.get('aplicacion') or {}
    current_inst_name = (current_app.get('instrumento_nombre') or '').lower()

    intereses_app = None
    competencias_app = None

    if 'nteres' in current_inst_name:
        intereses_app = current_app
        # Buscar la competencia más reciente en mis_apps
        competencias_app = next((a for a in mis_apps if a.get('estado') == 'completada' and 'ompet' in (a.get('instrumento_nombre') or '').lower()), None)
    elif 'ompet' in current_inst_name:
        competencias_app = current_app
        # Buscar el interés más reciente en mis_apps
        intereses_app = next((a for a in mis_apps if a.get('estado') == 'completada' and 'nteres' in (a.get('instrumento_nombre') or '').lower()), None)
    else:
        # Fallback a los más recientes de cada uno si es otro tipo de instrumento
        intereses_app = next((a for a in mis_apps if a.get('estado') == 'completada' and 'nteres' in (a.get('instrumento_nombre') or '').lower()), None)
        competencias_app = next((a for a in mis_apps if a.get('estado') == 'completada' and 'ompet' in (a.get('instrumento_nombre') or '').lower()), None)


    intereses_puntajes = {}
    competencias_puntajes = {}
    if intereses_app:
        int_data, int_status = api_request('GET', f'/consultas/resultado/{intereses_app["id"]}')
        if int_status == 200:
            int_perfil = int_data.get('perfil') or {}
            intereses_puntajes = (int_perfil.get('datos_json') or {}).get('puntajes_por_area', {})
    if competencias_app:
        comp_data, comp_status = api_request('GET', f'/consultas/resultado/{competencias_app["id"]}')
        if comp_status == 200:
            comp_perfil = comp_data.get('perfil') or {}
            competencias_puntajes = (comp_perfil.get('datos_json') or {}).get('puntajes_por_area', {})

    # Unificar ambos puntajes
    comparativo = _unificar_puntajes_riasec(intereses_puntajes, competencias_puntajes, puntajes_area)

    # Sobrescribir en perfil para que la UI también use el comparativo unificado
    if perfil.get('datos_json'):
        perfil['datos_json']['puntajes_por_area'] = comparativo

    return render_template('estudiante/explorador.html',
                           perfil=perfil,
                           puntajes=comparativo,
                           aplicacion_id=aplicacion_id)


@estudiante_routes.route('/api/pln/analizar', methods=['POST'])
@login_required
def api_pln_analizar():
    """Proxy PLN para el estudiante — analiza texto libre y retorna scores RIASEC."""
    from flask import jsonify as _j
    body = request.get_json() or {}
    data, status = api_request('POST', '/ml/pln/analizar-texto', body)
    return _j(data), status
