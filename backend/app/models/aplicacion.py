"""Modelos de aplicación del instrumento, configuración y respuestas."""

from ..extensions import db
from datetime import datetime
from sqlalchemy import Index


class ConfiguracionAplicacion(db.Model):
    __tablename__ = 'configuraciones_aplicacion'

    id = db.Column(db.Integer, primary_key=True)
    instrumento_id = db.Column(db.Integer, db.ForeignKey('instrumentos.id', ondelete='CASCADE'), nullable=False)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    fecha_inicio = db.Column(db.DateTime, nullable=False)
    fecha_fin = db.Column(db.DateTime, nullable=False)
    obligatoria = db.Column(db.Boolean, default=False)
    institucion_id = db.Column(db.Integer, db.ForeignKey('instituciones.id', ondelete='SET NULL'))
    grado_id = db.Column(db.Integer, db.ForeignKey('grados.id', ondelete='SET NULL'))
    cohorte = db.Column(db.String(10))
    activa = db.Column(db.Boolean, default=True)
    creado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    aplicaciones = db.relationship('Aplicacion', backref='configuracion', lazy='dynamic')
    institucion = db.relationship('Institucion', backref='configuraciones')
    grado = db.relationship('Grado', backref='configuraciones')
    creador = db.relationship('Usuario', backref='configuraciones_creadas', foreign_keys=[creado_por])

    def to_dict(self):
        return {
            'id': self.id,
            'instrumento_id': self.instrumento_id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'fecha_inicio': self.fecha_inicio.isoformat() if self.fecha_inicio else None,
            'fecha_fin': self.fecha_fin.isoformat() if self.fecha_fin else None,
            'obligatoria': self.obligatoria,
            'institucion_id': self.institucion_id,
            'grado_id': self.grado_id,
            'cohorte': self.cohorte,
            'activa': self.activa,
        }


class Aplicacion(db.Model):
    __tablename__ = 'aplicaciones'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False)
    configuracion_id = db.Column(db.Integer, db.ForeignKey('configuraciones_aplicacion.id', ondelete='CASCADE'), nullable=False)
    estado = db.Column(db.String(20), default='en_progreso')
    progreso = db.Column(db.Integer, default=0)
    fecha_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_fin = db.Column(db.DateTime)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    respuestas = db.relationship('Respuesta', backref='aplicacion', lazy='dynamic', cascade='all, delete-orphan')
    resultados = db.relationship('ResultadoDimension', backref='aplicacion', lazy='dynamic', cascade='all, delete-orphan')
    perfil = db.relationship('PerfilVocacional', backref='aplicacion', uselist=False, cascade='all, delete-orphan')

    # Índices compuestos para acelerar los COUNT/filtros más frecuentes
    __table_args__ = (
        Index('idx_aplicaciones_config_estado',  'configuracion_id', 'estado'),
        Index('idx_aplicaciones_usuario_estado', 'usuario_id',       'estado'),
        Index('idx_aplicaciones_fecha_estado',   'fecha_inicio',     'estado'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'configuracion_id': self.configuracion_id,
            'instrumento_nombre': self.configuracion.instrumento.nombre if self.configuracion and self.configuracion.instrumento else None,
            'obligatoria': self.configuracion.obligatoria if self.configuracion else False,
            'estado': self.estado,
            'progreso': self.progreso,
            'fecha_inicio': self.fecha_inicio.isoformat() if self.fecha_inicio else None,
            'fecha_fin': self.fecha_fin.isoformat() if self.fecha_fin else None,
        }


class Respuesta(db.Model):
    __tablename__ = 'respuestas'

    id = db.Column(db.Integer, primary_key=True)
    aplicacion_id = db.Column(db.Integer, db.ForeignKey('aplicaciones.id', ondelete='CASCADE'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id', ondelete='CASCADE'), nullable=False)
    valor = db.Column(db.Integer)
    valor_texto = db.Column(db.Text)
    tiempo_respuesta_seg = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('aplicacion_id', 'item_id'),)

    def to_dict(self):
        return {
            'id': self.id,
            'aplicacion_id': self.aplicacion_id,
            'item_id': self.item_id,
            'valor': self.valor,
            'valor_texto': self.valor_texto,
            'tiempo_respuesta_seg': self.tiempo_respuesta_seg,
        }
