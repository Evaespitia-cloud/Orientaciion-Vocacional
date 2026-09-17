"""Rutas de autenticación — login, registro, logout, consentimiento."""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from ..utils import api_request

auth_routes = Blueprint('auth', __name__)


@auth_routes.route('/login', methods=['GET', 'POST'])
def login():
    """Página de inicio de sesión."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        data, status = api_request('POST', '/auth/login', {
            'email': email,
            'password': password,
        })

        if status == 200:
            session['access_token'] = data['access_token']
            session['usuario'] = data['usuario']
            session['rol'] = data['usuario']['rol']['nombre']
            session['usuario_id'] = data['usuario']['id']
            session['nombre'] = data['usuario']['nombre_completo']

            # Redirigir según rol
            rol = session['rol']
            if rol in ('bienestar', 'ti', 'directivo', 'investigador'):
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('estudiante.inicio'))
        else:
            error = data.get('error', 'Error al iniciar sesión')
            if error == 'Cuenta inactiva':
                flash('Tu cuenta está inactiva. Comunícate con el administrador para reactivarla.', 'error')
            else:
                flash(error, 'error')

    return render_template('auth/login.html')


@auth_routes.route('/registro', methods=['GET', 'POST'])
def registro():
    """Página de registro de estudiante con contraseña propia.

    Si el registro falla (contraseña sin carácter especial, correo repetido, etc.)
    se vuelve a mostrar el formulario con los datos ya diligenciados para que el
    usuario no tenga que escribirlo todo de nuevo. Por seguridad, los campos de
    contraseña sí se vacían.
    """
    if request.method == 'POST':
        rol = 'estudiante'
        datos = {
            'email': request.form.get('email'),
            'nombres': request.form.get('nombres'),
            'apellidos': request.form.get('apellidos'),
            'documento': request.form.get('documento'),
            'tipo_documento': request.form.get('tipo_documento', 'CC'),
            'telefono': request.form.get('telefono'),
            'grado_id': request.form.get('grado_id', type=int),
            'semestre': request.form.get('semestre', type=int),
            'genero': request.form.get('genero') or None,
            'rol': rol,
        }

        # Datos que se devuelven al formulario si algo falla (sin contraseñas)
        form_previo = {k: v for k, v in request.form.items()
                       if k not in ('password', 'password_confirm', '_csrf_token')}

        password = request.form.get('password') or ''
        password_confirm = request.form.get('password_confirm') or ''
        if password != password_confirm:
            flash('Las contraseñas no coinciden. Vuelve a escribirlas; el resto de tus datos se conservó.', 'error')
            return render_template('auth/registro.html', form=form_previo)
        datos['password'] = password

        data, status = api_request('POST', '/auth/registro', datos)

        if status == 201:
            flash('Registro exitoso. Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('auth.login'))

        error = data.get('error', 'Error en el registro')
        if 'contraseña' in error.lower():
            error += ' Vuelve a escribir la contraseña; el resto de tus datos se conservó.'
        flash(error, 'error')
        return render_template('auth/registro.html', form=form_previo)

    return render_template('auth/registro.html', form={})


@auth_routes.route('/consentimiento', methods=['GET', 'POST'])
def consentimiento():
    """Página de consentimiento de tratamiento de datos."""
    if 'access_token' not in session:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        aceptado = request.form.get('aceptado') == 'si'
        data, status = api_request('POST', '/consentimiento/', {
            'aceptado': aceptado,
            'version': '1.0',
        })

        if status == 201 and aceptado:
            session['consentimiento'] = True
            return redirect(url_for('estudiante.inicio'))
        elif not aceptado:
            flash('Debes aceptar el consentimiento para continuar.', 'warning')

    # Obtener estado del consentimiento
    data, status = api_request('GET', '/consentimiento/estado')
    texto_politica = data.get('texto_politica', '') if status == 200 else ''
    tiene_consentimiento = data.get('tiene_consentimiento', False) if status == 200 else False

    if tiene_consentimiento:
        session['consentimiento'] = True
        return redirect(url_for('estudiante.inicio'))

    return render_template('auth/consentimiento.html', texto_politica=texto_politica)


@auth_routes.route('/logout', methods=['POST'])
def logout():
    """Cerrar sesión."""
    if 'access_token' in session:
        api_request('POST', '/auth/logout')
    session.clear()
    flash('Sesión cerrada exitosamente.', 'success')
    return redirect(url_for('auth.login'))
