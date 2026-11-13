"""Catálogo de colegios del Valle de Aburrá y datos escolares de cada estudiante.

Son tablas nuevas a propósito: ``db.create_all()`` las crea en una base que ya
existe sin tocar las demás, así que no hace falta una migración en Render.
"""

from datetime import datetime

from ..extensions import db
from ..utils import nombres_colegios as nombres


class SedeEducativa(db.Model):
    __tablename__ = 'sedes_educativas'

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    codigo_establecimiento = db.Column(db.String(20))
    nombre = db.Column(db.String(200), nullable=False)
    sede = db.Column(db.String(200))
    sector = db.Column(db.String(10), nullable=False)  # Oficial | Privado
    municipio = db.Column(db.String(30), nullable=False, index=True)
    comuna = db.Column(db.String(80))
    barrio = db.Column(db.String(80))
    direccion = db.Column(db.String(200))
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    matricula_9 = db.Column(db.Integer)
    matricula_10 = db.Column(db.Integer)
    matricula_11 = db.Column(db.Integer)
    fuente = db.Column(db.String(120))
    ubicacion = db.Column(db.String(30))  # de dónde salió la coordenada

    @property
    def matricula_media(self):
        valores = [self.matricula_9, self.matricula_10, self.matricula_11]
        return None if all(v is None for v in valores) else sum(v or 0 for v in valores)

    @property
    def nombre_limpio(self):
        """El nombre como se muestra: sin abreviaturas ni mayúsculas sostenidas."""
        return nombres.limpiar_nombre(self.nombre)

    @property
    def sede_etiqueta(self):
        """"Sede Municipal Kennedy" cuando no es la sede principal; None si lo es."""
        return nombres.etiqueta_sede(self.nombre, self.sede)

    @property
    def municipio_nombre(self):
        return nombres.nombre_municipio(self.municipio)

    @property
    def nombre_visible(self):
        return nombres.nombre_con_sede(self.nombre, self.sede)

    def to_dict(self):
        return {
            'codigo': self.codigo, 'nombre': self.nombre_limpio, 'sede': self.sede,
            'sede_etiqueta': self.sede_etiqueta, 'nombre_visible': self.nombre_visible,
            'sector': self.sector, 'municipio': self.municipio, 'municipio_nombre': self.municipio_nombre,
            'comuna': self.comuna, 'barrio': self.barrio,
            'direccion': self.direccion, 'lat': self.lat, 'lon': self.lon,
            'matricula_media': self.matricula_media, 'fuente': self.fuente,
        }


class PerfilEscolar(db.Model):
    """Colegio, edad y dirección de un estudiante (una fila por estudiante)."""

    __tablename__ = 'perfiles_escolares'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='CASCADE'), unique=True, nullable=False)
    sede_codigo = db.Column(db.String(20), db.ForeignKey('sedes_educativas.codigo', ondelete='SET NULL'))
    colegio_texto = db.Column(db.String(200))  # cuando el colegio no está en el catálogo
    sector = db.Column(db.String(10))
    edad = db.Column(db.Integer)
    municipio = db.Column(db.String(30))
    direccion = db.Column(db.String(200))
    direccion_normalizada = db.Column(db.String(120))
    complemento = db.Column(db.String(80))
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    precision = db.Column(db.String(20))  # exacta | interpolada | cuadra | osm | manual
    estrato = db.Column(db.Integer)
    simulado = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sede_rel = db.relationship('SedeEducativa')
    usuario = db.relationship('Usuario', backref=db.backref('perfil_escolar', uselist=False))

    @property
    def colegio(self):
        return self.sede_rel.nombre_visible if self.sede_rel else self.colegio_texto

    @property
    def completo(self):
        return bool((self.sede_codigo or self.colegio_texto) and self.edad and self.lat is not None)

    def to_dict(self):
        return {
            'sede_codigo': self.sede_codigo, 'colegio': self.colegio, 'colegio_texto': self.colegio_texto,
            'sector': self.sector, 'edad': self.edad, 'municipio': self.municipio,
            'direccion': self.direccion, 'direccion_normalizada': self.direccion_normalizada,
            'complemento': self.complemento, 'lat': self.lat, 'lon': self.lon,
            'precision': self.precision, 'estrato': self.estrato, 'completo': self.completo,
        }
