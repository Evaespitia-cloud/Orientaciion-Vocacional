"""Modelos ORM para los módulos de Machine Learning: Clustering y PLN."""

from ..extensions import db
from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ClusteringResultado(db.Model):
    """Resultado de una ejecución del algoritmo de clustering K-Means."""
    __tablename__ = 'clustering_resultados'

    id = db.Column(db.Integer, primary_key=True)
    configuracion_id = db.Column(db.Integer, db.ForeignKey('configuraciones_aplicacion.id', ondelete='SET NULL'))
    n_clusters = db.Column(db.Integer, nullable=False)
    silhouette_score = db.Column(db.Numeric(6, 4))
    inertia = db.Column(db.Numeric(14, 4))
    centroides = db.Column(db.JSON)
    descripcion_clusters = db.Column(db.JSON)
    n_aplicaciones = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=_now)

    asignaciones = db.relationship('ClusteringAsignacion', backref='resultado', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'configuracion_id': self.configuracion_id,
            'n_clusters': self.n_clusters,
            'silhouette_score': float(self.silhouette_score) if self.silhouette_score else None,
            'inertia': float(self.inertia) if self.inertia else None,
            'centroides': self.centroides,
            'descripcion_clusters': self.descripcion_clusters,
            'n_aplicaciones': self.n_aplicaciones,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ClusteringAsignacion(db.Model):
    """Asignación de una aplicación a un cluster."""
    __tablename__ = 'clustering_asignaciones'

    id = db.Column(db.Integer, primary_key=True)
    clustering_resultado_id = db.Column(db.Integer, db.ForeignKey('clustering_resultados.id', ondelete='CASCADE'), nullable=False)
    aplicacion_id = db.Column(db.Integer, db.ForeignKey('aplicaciones.id', ondelete='CASCADE'), nullable=False)
    cluster_id = db.Column(db.Integer, nullable=False)
    distancia_centroide = db.Column(db.Numeric(10, 4))
    created_at = db.Column(db.DateTime, default=_now)

    __table_args__ = (db.UniqueConstraint('clustering_resultado_id', 'aplicacion_id'),)

    aplicacion = db.relationship('Aplicacion', backref='clustering_asignaciones')

    def to_dict(self):
        return {
            'id': self.id,
            'aplicacion_id': self.aplicacion_id,
            'cluster_id': self.cluster_id,
            'distancia_centroide': float(self.distancia_centroide) if self.distancia_centroide else None,
        }


class PlnAnalisis(db.Model):
    """Resultado del análisis PLN sobre una respuesta abierta."""
    __tablename__ = 'pln_analisis'

    id = db.Column(db.Integer, primary_key=True)
    respuesta_id = db.Column(db.Integer, db.ForeignKey('respuestas.id', ondelete='CASCADE'), nullable=False, unique=True)
    texto_original = db.Column(db.Text)
    texto_procesado = db.Column(db.Text)
    palabras_clave = db.Column(db.JSON)
    scores_riasec = db.Column(db.JSON)
    area_dominante = db.Column(db.String(50))
    confianza = db.Column(db.Numeric(5, 4))
    created_at = db.Column(db.DateTime, default=_now)

    respuesta = db.relationship('Respuesta', backref=db.backref('pln_analisis', uselist=False))

    def to_dict(self):
        return {
            'id': self.id,
            'respuesta_id': self.respuesta_id,
            'texto_original': self.texto_original,
            'palabras_clave': self.palabras_clave,
            'scores_riasec': self.scores_riasec,
            'area_dominante': self.area_dominante,
            'confianza': float(self.confianza) if self.confianza else None,
        }
