"""Utilidades para guardar datos demográficos de un usuario.

El género no es una columna de `usuarios`: se almacena como dato demográfico,
igual que el resto de variables de caracterización. Así alimenta directamente
el reporte de segmentación por género que ya existe en el panel, sin tocar el
esquema de la tabla de usuarios.
"""

from ..extensions import db
from ..models.demografico import CampoDemografico, DatoDemografico

OPCIONES_GENERO = ['Masculino', 'Femenino', 'Prefiero no decirlo']


def guardar_genero(usuario_id: int, valor) -> bool:
    """Registrar (o actualizar) el género de un usuario.

    Devuelve True si se guardó. Un valor vacío o fuera de las opciones válidas
    se ignora en silencio: el género es opcional y nunca debe hacer fallar el
    registro de la persona.
    """
    valor = str(valor or '').strip()
    if valor not in OPCIONES_GENERO:
        return False

    campo = CampoDemografico.query.filter_by(nombre='genero').first()
    if not campo:
        orden = db.session.query(db.func.max(CampoDemografico.orden)).scalar() or 0
        campo = CampoDemografico(
            nombre='genero', etiqueta='Género', tipo_campo='select',
            opciones=OPCIONES_GENERO, obligatorio=False, activo=True, orden=orden + 1,
        )
        db.session.add(campo)
        db.session.flush()

    dato = DatoDemografico.query.filter_by(usuario_id=usuario_id, campo_id=campo.id).first()
    if dato:
        dato.valor = valor
    else:
        db.session.add(DatoDemografico(usuario_id=usuario_id, campo_id=campo.id, valor=valor))

    db.session.commit()
    return True
