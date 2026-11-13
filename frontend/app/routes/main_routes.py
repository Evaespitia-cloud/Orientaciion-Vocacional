"""Rutas principales."""

from flask import Blueprint, redirect, url_for, session, jsonify, render_template, request, flash, abort, Response
from ..utils import api_request, api_request_file

main_routes = Blueprint('main', __name__)


@main_routes.route('/')
def index():
    """Mostrar landing page o redirigir al dashboard/inicio según sesión."""
    if 'access_token' in session:
        rol = session.get('rol', 'estudiante')
        if rol in ('bienestar', 'ti', 'directivo', 'investigador'):
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('estudiante.inicio'))
    data, status = api_request('GET', '/compartir/ejemplos')
    ejemplos = data.get('codigos', []) if status == 200 else []
    return render_template('landing.html', cartas_ejemplo=ejemplos)


def _png_de_carta(codigo, formato):
    resp = api_request_file('GET', f'/compartir/publico/{codigo}.png',
                            params={'formato': formato, 'sitio': request.host})
    if resp is None or resp.status_code != 200:
        abort(404)
    r = Response(resp.content, mimetype='image/png')
    r.headers['Cache-Control'] = 'public, max-age=86400'
    return r


@main_routes.route('/r/<codigo>')
def carta_publica(codigo):
    """Página pública de una carta compartida: sin datos personales, solo el perfil."""
    data, status = api_request('GET', f'/compartir/publico/{codigo}')
    if status != 200:
        abort(404)
    return render_template('compartir.html', codigo=codigo, carta=data)


@main_routes.route('/r/<codigo>/carta.png')
def carta_publica_png(codigo):
    return _png_de_carta(codigo, 'historia')


@main_routes.route('/r/<codigo>/enlace.png')
def carta_publica_enlace(codigo):
    return _png_de_carta(codigo, 'enlace')


@main_routes.route('/perfil', methods=['GET', 'POST'])
def perfil():
    """Perfil del usuario autenticado — ver y editar datos personales."""
    if 'access_token' not in session:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        datos = {
            'nombres': request.form.get('nombres', '').strip(),
            'apellidos': request.form.get('apellidos', '').strip(),
            'telefono': request.form.get('telefono', '').strip(),
        }
        pwd_actual = request.form.get('password_actual', '').strip()
        pwd_nueva = request.form.get('password_nueva', '').strip()
        if pwd_actual and pwd_nueva:
            datos['password_actual'] = pwd_actual
            datos['password_nueva'] = pwd_nueva

        data, status = api_request('PUT', '/auth/perfil', datos)
        if status == 200:
            # Actualizar nombre en sesión
            u = data.get('usuario', {})
            session['nombre'] = f"{u.get('nombres', '')} {u.get('apellidos', '')}".strip()
            flash('Perfil actualizado correctamente.', 'success')
        else:
            flash(data.get('error', 'Error al actualizar el perfil.'), 'error')
        return redirect(url_for('main.perfil'))

    data, status = api_request('GET', '/auth/perfil')
    if status != 200:
        flash('No se pudo cargar el perfil.', 'error')
        return redirect(url_for('main.index'))

    return render_template('perfil.html', usuario=data.get('usuario', {}))


@main_routes.route('/api/colegios')
def colegios_publicos():
    """Proxy público del buscador de colegios (lo usa también el registro, sin sesión)."""
    data, status = api_request('GET', '/escolar/colegios', params={
        'q': request.args.get('q', '')[:80], 'municipio': request.args.get('municipio', ''),
        # Oficial o privado: es lo que filtra la lista del registro.
        'sector': request.args.get('sector', ''),
    })
    return jsonify(data), status


@main_routes.route('/api/grados-publicos')
def grados_publicos():
    """Proxy público: devuelve lista de grados al formulario de registro (sin auth)."""
    data, status = api_request('GET', '/auth/grados')
    return jsonify(data), status
