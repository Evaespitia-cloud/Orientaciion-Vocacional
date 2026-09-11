"""Flask application factory para el frontend."""

import os
from flask import Flask, render_template, session, current_app, request, abort
from flask_session import Session
import hmac
import secrets
from .config import config_by_name, validate_production_environment


def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    if config_name not in config_by_name:
        raise ValueError(f'Entorno no soportado: {config_name}')
    validate_production_environment(config_name)

    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')
    app.config.from_object(config_by_name[config_name])
    os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
    Session(app)

    def _csrf_token():
        token = session.get('_csrf_token')
        if not token:
            token = secrets.token_urlsafe(32)
            session['_csrf_token'] = token
        return token

    app.jinja_env.globals['csrf_token'] = _csrf_token

    @app.before_request
    def csrf_protect():
        if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
            expected = session.get('_csrf_token')
            supplied = request.form.get('_csrf_token') or request.headers.get('X-CSRF-Token')
            if not expected or not supplied or not hmac.compare_digest(str(expected), str(supplied)):
                abort(400)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        response.headers.setdefault('Content-Security-Policy', "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; connect-src 'self'; font-src 'self' data: https://cdn.jsdelivr.net https://fonts.gstatic.com")
        if config_name == 'production':
            response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        return response

    # Contexto global: expone la URL del backend y el token JWT a todos los templates
    @app.context_processor
    def inject_globals():
        return {
            'api_base': app.config.get('BACKEND_API_URL', 'http://localhost:5000/api'),
            'current_user': {
                'nombre': session.get('nombre', ''),
                'rol': session.get('rol', ''),
                'email': session.get('email', ''),
            },
        }

    # Registrar rutas
    from .routes.auth_routes import auth_routes
    from .routes.estudiante_routes import estudiante_routes
    from .routes.admin_routes import admin_bp
    from .routes.main_routes import main_routes

    app.register_blueprint(main_routes)
    app.register_blueprint(auth_routes, url_prefix='/auth')
    app.register_blueprint(estudiante_routes, url_prefix='/estudiante')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Manejadores de error
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template('500.html'), 500

    return app
