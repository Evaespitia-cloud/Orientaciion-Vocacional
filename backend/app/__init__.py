"""Flask application factory para el backend API."""

import os
from flask import Flask
from .config import config_by_name, validate_production_environment
from .extensions import db, migrate, jwt, cors


def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    if config_name not in config_by_name:
        raise ValueError(f'Entorno no soportado: {config_name}')
    validate_production_environment(config_name)

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Inicializar extensiones
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    allowed_origins = [o.strip() for o in os.getenv('ALLOWED_ORIGINS', 'http://localhost:5001').split(',') if o.strip()]
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": allowed_origins}},
        supports_credentials=False,
        methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
        allow_headers=['Content-Type', 'Authorization'],
    )

    @app.after_request
    def security_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('Referrer-Policy', 'no-referrer')
        response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        response.headers.setdefault('Cache-Control', 'no-store')
        if config_name == 'production':
            response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        return response

    # Registrar blueprints (controladores)
    from .controllers.auth_controller import auth_bp
    from .controllers.usuario_controller import usuario_bp
    from .controllers.consentimiento_controller import consentimiento_bp
    from .controllers.config_controller import config_bp
    from .controllers.instrumento_controller import instrumento_bp
    from .controllers.aplicacion_controller import aplicacion_bp
    from .controllers.procesamiento_controller import procesamiento_bp
    from .controllers.reporte_controller import reporte_bp
    from .controllers.estadistica_controller import estadistica_bp
    from .controllers.consulta_controller import consulta_bp
    from .controllers.exportacion_controller import exportacion_bp
    from .controllers.auditoria_controller import auditoria_bp
    from .controllers.demografico_controller import demografico_bp
    from .controllers.ml_controller import ml_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(usuario_bp, url_prefix='/api/usuarios')
    app.register_blueprint(consentimiento_bp, url_prefix='/api/consentimiento')
    app.register_blueprint(config_bp, url_prefix='/api/configuracion')
    app.register_blueprint(instrumento_bp, url_prefix='/api/instrumentos')
    app.register_blueprint(aplicacion_bp, url_prefix='/api/aplicaciones')
    app.register_blueprint(procesamiento_bp, url_prefix='/api/procesamiento')
    app.register_blueprint(reporte_bp, url_prefix='/api/reportes')
    app.register_blueprint(estadistica_bp, url_prefix='/api/estadisticas')
    app.register_blueprint(consulta_bp, url_prefix='/api/consultas')
    app.register_blueprint(exportacion_bp, url_prefix='/api/exportacion')
    app.register_blueprint(auditoria_bp, url_prefix='/api/auditoria')
    app.register_blueprint(demografico_bp, url_prefix='/api/demografico')
    app.register_blueprint(ml_bp, url_prefix='/api/ml')

    # Ruta de health check
    @app.route('/api/health')
    def health():
        return {'status': 'ok', 'message': 'API Orientación Vocacional funcionando'}

    # Manejadores de error globales
    from flask import jsonify as _jsonify

    @app.errorhandler(404)
    def not_found(e):
        return _jsonify({'error': 'Recurso no encontrado'}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return _jsonify({'error': 'Método no permitido'}), 405

    @app.errorhandler(500)
    def internal_error(e):
        return _jsonify({'error': 'Error interno del servidor'}), 500

    return app
