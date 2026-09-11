"""Modelos de usuario, rol, permiso y consentimiento."""

from ..extensions import db
from datetime import datetime


class Rol(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.Text)
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    usuarios = db.relationship('Usuario', backref='rol', lazy='dynamic')
    permisos = db.relationship('Permiso', secondary='rol_permisos', backref=db.backref('roles', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'activo': self.activo,
        }


class Permiso(db.Model):
    __tablename__ = 'permisos'

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(100), unique=True, nullable=False)
    descripcion = db.Column(db.Text)
    modulo = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'codigo': self.codigo,
            'descripcion': self.descripcion,
            'modulo': self.modulo,
        }


class RolPermiso(db.Model):
    __tablename__ = 'rol_permisos'

    id = db.Column(db.Integer, primary_key=True)
    rol_id = db.Column(db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    permiso_id = db.Column(db.Integer, db.ForeignKey('permisos.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('rol_id', 'permiso_id'),)


class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    nombres = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=False)
    documento = db.Column(db.String(20), unique=True)
    tipo_documento = db.Column(db.String(20), default='CC')
    telefono = db.Column(db.String(20))
    rol_id = db.Column(db.Integer, db.ForeignKey('roles.id', ondelete='RESTRICT'), nullable=False)
    grado_id = db.Column(db.Integer, db.ForeignKey('grados.id', ondelete='SET NULL'))
    semestre = db.Column(db.Integer)
    cohorte = db.Column(db.String(10))
    activo = db.Column(db.Boolean, default=True)
    ultimo_acceso = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    consentimientos = db.relationship('Consentimiento', backref='usuario', lazy='dynamic')
    aplicaciones = db.relationship('Aplicacion', backref='usuario', lazy='dynamic')

    @property
    def nombre_completo(self):
        return f'{self.nombres} {self.apellidos}'

    def to_dict(self, include_sensitive=False):
        data = {
            'id': self.id,
            'email': self.email,
            'nombres': self.nombres,
            'apellidos': self.apellidos,
            'nombre_completo': f'{self.nombres} {self.apellidos}',
            'documento': self.documento,
            'tipo_documento': self.tipo_documento,
            'telefono': self.telefono,
            'rol': self.rol.to_dict() if self.rol else None,
            'grado_id': self.grado_id,
            'grado_nombre': self.grado.nombre if self.grado else None,
            'semestre': self.semestre,
            'cohorte': self.cohorte,
            'activo': self.activo,
            'ultimo_acceso': self.ultimo_acceso.isoformat() if self.ultimo_acceso else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        return data


class Consentimiento(db.Model):
    __tablename__ = 'consentimientos'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False)
    version_politica = db.Column(db.String(20), nullable=False, default='1.0')
    texto_politica = db.Column(db.Text, nullable=False)
    aceptado = db.Column(db.Boolean, nullable=False, default=False)
    ip_address = db.Column(db.String(45))
    fecha_aceptacion = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'version_politica': self.version_politica,
            'aceptado': self.aceptado,
            'fecha_aceptacion': self.fecha_aceptacion.isoformat() if self.fecha_aceptacion else None,
        }
