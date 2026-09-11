"""Modelos de resultados, perfiles vocacionales y reportes."""

from ..extensions import db
from datetime import datetime


class ResultadoDimension(db.Model):
    __tablename__ = 'resultados_dimension'

    id = db.Column(db.Integer, primary_key=True)
    aplicacion_id = db.Column(db.Integer, db.ForeignKey('aplicaciones.id', ondelete='CASCADE'), nullable=False)
    dimension_id = db.Column(db.Integer, db.ForeignKey('dimensiones.id', ondelete='CASCADE'), nullable=False)
    puntaje_bruto = db.Column(db.Numeric(10, 2), nullable=False)
    puntaje_normalizado = db.Column(db.Numeric(5, 2))
    nivel = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('aplicacion_id', 'dimension_id'),)

    def to_dict(self):
        return {
            'id': self.id,
            'aplicacion_id': self.aplicacion_id,
            'dimension_id': self.dimension_id,
            'dimension_nombre': self.dimension.nombre if self.dimension else None,
            'puntaje_bruto': float(self.puntaje_bruto),
            'puntaje_normalizado': float(self.puntaje_normalizado) if self.puntaje_normalizado else None,
            'nivel': self.nivel,
        }


class PerfilVocacional(db.Model):
    __tablename__ = 'perfiles_vocacionales'

    id = db.Column(db.Integer, primary_key=True)
    aplicacion_id = db.Column(db.Integer, db.ForeignKey('aplicaciones.id', ondelete='CASCADE'), nullable=False, unique=True)
    perfil_principal = db.Column(db.String(100), nullable=False)
    perfil_secundario = db.Column(db.String(100))
    descripcion = db.Column(db.Text)
    fortalezas = db.Column(db.Text)
    areas_desarrollo = db.Column(db.Text)
    recomendaciones = db.Column(db.Text)
    datos_json = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reportes = db.relationship('Reporte', backref='perfil', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'aplicacion_id': self.aplicacion_id,
            'perfil_principal': self.perfil_principal,
            'perfil_secundario': self.perfil_secundario,
            'descripcion': self.descripcion,
            'fortalezas': self.fortalezas,
            'areas_desarrollo': self.areas_desarrollo,
            'recomendaciones': self.recomendaciones,
            'datos_json': self.datos_json,
        }


class Reporte(db.Model):
    __tablename__ = 'reportes'

    id = db.Column(db.Integer, primary_key=True)
    perfil_id = db.Column(db.Integer, db.ForeignKey('perfiles_vocacionales.id', ondelete='CASCADE'), nullable=False)
    tipo = db.Column(db.String(30), default='individual')
    ruta_archivo = db.Column(db.String(500))
    formato = db.Column(db.String(10), default='pdf')
    generado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    descargado = db.Column(db.Boolean, default=False)
    fecha_descarga = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    generador = db.relationship('Usuario', backref='reportes_generados', foreign_keys=[generado_por])

    def to_dict(self):
        return {
            'id': self.id,
            'perfil_id': self.perfil_id,
            'tipo': self.tipo,
            'formato': self.formato,
            'descargado': self.descargado,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
