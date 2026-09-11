"""Modelos de formulario demográfico configurable."""

from ..extensions import db
from datetime import datetime


class CampoDemografico(db.Model):
    __tablename__ = 'campos_demograficos'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    etiqueta = db.Column(db.String(200), nullable=False)
    tipo_campo = db.Column(db.String(30), nullable=False, default='texto')
    opciones = db.Column(db.JSON)
    obligatorio = db.Column(db.Boolean, default=True)
    activo = db.Column(db.Boolean, default=True)
    orden = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    datos = db.relationship('DatoDemografico', backref='campo', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'etiqueta': self.etiqueta,
            'tipo_campo': self.tipo_campo,
            'opciones': self.opciones,
            'obligatorio': self.obligatorio,
            'activo': self.activo,
            'orden': self.orden,
        }


class DatoDemografico(db.Model):
    __tablename__ = 'datos_demograficos'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False)
    campo_id = db.Column(db.Integer, db.ForeignKey('campos_demograficos.id', ondelete='CASCADE'), nullable=False)
    valor = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('usuario_id', 'campo_id'),)

    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'campo_id': self.campo_id,
            'campo_nombre': self.campo.nombre if self.campo else None,
            'campo_etiqueta': self.campo.etiqueta if self.campo else None,
            'valor': self.valor,
        }


class FormulaCalculo(db.Model):
    __tablename__ = 'formulas_calculo'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    tipo = db.Column(db.String(50), nullable=False, default='holland_riasec')
    parametros = db.Column(db.JSON, nullable=False, default={})
    activa = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'tipo': self.tipo,
            'parametros': self.parametros,
            'activa': self.activa,
        }
