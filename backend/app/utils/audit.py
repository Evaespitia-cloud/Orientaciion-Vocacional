"""Utilidad de auditoría para registrar acciones en el sistema."""

from ..extensions import db
from ..models.auditoria import Auditoria


def registrar_auditoria(usuario_id, accion, modulo, descripcion=None,
                        datos_anteriores=None, datos_nuevos=None, ip_address=None):
    """Registra una acción de auditoría."""
    registro = Auditoria(
        usuario_id=usuario_id,
        accion=accion,
        modulo=modulo,
        descripcion=descripcion,
        datos_anteriores=datos_anteriores,
        datos_nuevos=datos_nuevos,
        ip_address=ip_address,
    )
    db.session.add(registro)
    db.session.commit()
    return registro
