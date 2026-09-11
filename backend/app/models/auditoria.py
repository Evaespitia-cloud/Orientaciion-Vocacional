"""Modelos de auditoría y políticas de retención."""

from ..extensions import db
from datetime import datetime


class Auditoria(db.Model):
    __tablename__ = 'auditoria'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    accion = db.Column(db.String(100), nullable=False)
    modulo = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text)
    datos_anteriores = db.Column(db.JSON)
    datos_nuevos = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    usuario = db.relationship('Usuario', backref='auditorias')

    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'usuario_nombre': f'{self.usuario.nombres} {self.usuario.apellidos}' if self.usuario else 'Sistema',
            'accion': self.accion,
            'modulo': self.modulo,
            'descripcion': self.descripcion,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class PoliticaRetencion(db.Model):
    __tablename__ = 'politicas_retencion'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    tiempo_retencion_dias = db.Column(db.Integer, nullable=False, default=365)
    tabla_afectada = db.Column(db.String(100), nullable=False)
    activa = db.Column(db.Boolean, default=True)
    creado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creador = db.relationship('Usuario', backref='politicas_creadas', foreign_keys=[creado_por])

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'tiempo_retencion_dias': self.tiempo_retencion_dias,
            'tabla_afectada': self.tabla_afectada,
            'activa': self.activa,
        }
