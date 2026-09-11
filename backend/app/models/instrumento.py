"""Modelos del instrumento psicométrico."""

from ..extensions import db
from datetime import datetime


INTERESES_EXCEL_TEXTOS = [
    '¿Te gusta trabajar con herramientas, máquinas o equipos?',
    '¿Te gusta trabajar con herramientas, máquinas o equipos técnicos?',
    '¿Disfrutas las actividades al aire libre o físicas?',
    '¿Disfrutas las actividades físicas o al aire libre?',
    '¿Te interesa reparar o construir cosas con tus manos?',
    '¿Prefieres las actividades prácticas sobre las teóricas?',
    '¿Te gusta operar maquinaria o vehículos?',
    '¿Te gustaría trabajar en ingeniería, mecánica o construcción?',
    '¿Te gusta resolver problemas complejos mediante el análisis?',
    '¿Disfrutas investigar y descubrir cómo funcionan las cosas?',
    '¿Te interesa realizar experimentos o estudios científicos?',
    '¿Te gusta leer artículos científicos o documentales?',
    '¿Te gusta leer artículos científicos o de divulgación?',
    '¿Disfrutas trabajando con datos, números y estadísticas?',
    '¿Te gusta expresarte a través del arte, la música o la escritura?',
    '¿Disfrutas diseñando cosas nuevas e innovadoras?',
    '¿Te atrae trabajar en ambientes que valoran la creatividad?',
    '¿Te gusta actuar, cantar, bailar o tocar un instrumento?',
    '¿Prefieres encontrar soluciones originales a los problemas?',
    '¿Te satisface ayudar a otras personas a resolver sus problemas?',
    '¿Disfrutas enseñando o capacitando a otros?',
    '¿Te gusta trabajar en equipo y colaborar con otros?',
    '¿Te gusta trabajar en equipo y colaborar con compañeros?',
    '¿Te interesa el bienestar emocional y social de las personas?',
    '¿Te gustaría trabajar como consejero, profesor o terapeuta?',
    '¿Te gusta liderar equipos y tomar decisiones?',
    '¿Te gusta liderar equipos y tomar decisiones importantes?',
    '¿Te interesa crear y administrar tu propio negocio?',
    '¿Disfrutas persuadiendo o convenciendo a otros?',
    '¿Te motiva competir y lograr metas ambiciosas?',
    '¿Te ves dirigiendo un proyecto o empresa en el futuro?',
    '¿Te gusta organizar información y mantener registros ordenados?',
    '¿Disfrutas seguir procedimientos y reglas establecidas?',
    '¿Te sientes cómodo/a trabajando con hojas de cálculo y bases de datos?',
    '¿Te sientes cómodo/a trabajando con hojas de cálculo o bases de datos?',
    '¿Prefieres un ambiente de trabajo estructurado y predecible?',
    '¿Te gusta la contabilidad, la administración o el archivo?',
    '¿Te gusta la contabilidad, la administración o el archivo de documentos?',
]

_INTERESES_EXCEL_NORMALIZADO = {texto.strip().lower() for texto in INTERESES_EXCEL_TEXTOS}


def normalizar_texto(texto):
    return (texto or '').strip().lower()


def filtrar_intereses_excel_textos(textos):
    """Devuelve solo los textos autorizados para la dimensión de Intereses.

    La regla es conservadora y de servicio: si un texto no aparece en el
    inventario Excel declarativo, el sistema lo elimina de la serialización y
    del cálculo del perfil para la prueba de intereses.
    """
    if not textos:
        return []
    return [texto for texto in textos if normalizar_texto(texto) in _INTERESES_EXCEL_NORMALIZADO]


def item_de_intereses_autorizado(item):
    """Compatibilidad histórica: permite que el banco de intereses real
    exista sin cortarse por una lista de textos Excel de referencia.

    El instrumento puede usar distintos textos de pregunta, pero la dimensión
    de intereses debe seguir siendo entregada completa al estudiante y al
    servicio psicométrico sin depender de una coincidencia literal de texto.
    """
    if not item:
        return False
    if not getattr(item, 'texto', None):
        return False
    # El flujo del cliente debe priorizar el contenido activo del banco.
    # El exhaustivo diccionario Excel sólo sirve como referencia documental,
    # no como sentencia de exclusión del ítem persistido.
    return True


class Instrumento(db.Model):
    __tablename__ = 'instrumentos'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    version = db.Column(db.String(20), nullable=False, default='1.0')
    activo = db.Column(db.Boolean, default=True)
    creado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    dimensiones = db.relationship('Dimension', backref='instrumento', lazy='dynamic', cascade='all, delete-orphan')
    configuraciones = db.relationship('ConfiguracionAplicacion', backref='instrumento', lazy='dynamic')
    creador = db.relationship('Usuario', backref='instrumentos_creados', foreign_keys=[creado_por])

    def to_dict(self, include_dimensiones=False, incluir_clave=True):
        data = {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'version': self.version,
            'activo': self.activo,
        }
        if include_dimensiones:
            data['dimensiones'] = [
                d.to_dict(include_escalas=True, incluir_clave=incluir_clave)
                for d in self.dimensiones.order_by(Dimension.orden)
            ]
        return data


class Dimension(db.Model):
    __tablename__ = 'dimensiones'

    id = db.Column(db.Integer, primary_key=True)
    instrumento_id = db.Column(db.Integer, db.ForeignKey('instrumentos.id', ondelete='CASCADE'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    peso = db.Column(db.Numeric(5, 2), default=1.0)
    orden = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    escalas = db.relationship('Escala', backref='dimension', lazy='dynamic', cascade='all, delete-orphan')
    resultados = db.relationship('ResultadoDimension', backref='dimension', lazy='dynamic')

    def to_dict(self, include_escalas=False, incluir_clave=True):
        data = {
            'id': self.id,
            'instrumento_id': self.instrumento_id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'peso': float(self.peso) if self.peso else 1.0,
            'orden': self.orden,
        }
        if include_escalas:
            data['escalas'] = [
                e.to_dict(include_items=True, incluir_clave=incluir_clave)
                for e in self.escalas.order_by(Escala.orden)
            ]
        return data


class Escala(db.Model):
    __tablename__ = 'escalas'

    id = db.Column(db.Integer, primary_key=True)
    dimension_id = db.Column(db.Integer, db.ForeignKey('dimensiones.id', ondelete='CASCADE'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    valor_minimo = db.Column(db.Integer, default=1)
    valor_maximo = db.Column(db.Integer, default=5)
    orden = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('Item', backref='escala', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self, include_items=False, incluir_clave=True):
        data = {
            'id': self.id,
            'dimension_id': self.dimension_id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'valor_minimo': self.valor_minimo,
            'valor_maximo': self.valor_maximo,
            'orden': self.orden,
        }
        if include_items:
            items = self.items.filter_by(activo=True).order_by(Item.orden).all()
            data['items'] = [
                i.to_dict(incluir_clave=incluir_clave)
                for i in items
            ]
        return data


class Item(db.Model):
    __tablename__ = 'items'

    id = db.Column(db.Integer, primary_key=True)
    escala_id = db.Column(db.Integer, db.ForeignKey('escalas.id', ondelete='CASCADE'), nullable=False)
    codigo = db.Column(db.String(20))
    texto = db.Column(db.Text, nullable=False)
    # Contexto/escenario de la situación (usado por ítems de juicio situacional)
    contexto = db.Column(db.Text)
    tipo = db.Column(db.String(30), default='likert')
    opciones = db.Column(db.JSON)
    obligatorio = db.Column(db.Boolean, default=True)
    orden = db.Column(db.Integer, default=0)
    activo = db.Column(db.Boolean, default=True)
    version = db.Column(db.String(10), default='1.0')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    respuestas = db.relationship('Respuesta', backref='item', lazy='dynamic')

    def _opciones_sin_clave(self):
        """Copia de `opciones` sin el puntaje de calificación (para no exponerlo al estudiante)."""
        ops = self.opciones
        if not isinstance(ops, dict):
            return ops
        limpio = dict(ops)
        if isinstance(limpio.get('opciones'), list):
            limpio['opciones'] = [
                {k: v for k, v in o.items() if k != 'puntaje'} if isinstance(o, dict) else o
                for o in limpio['opciones']
            ]
        return limpio

    def to_dict(self, incluir_clave=True):
        return {
            'id': self.id,
            'escala_id': self.escala_id,
            'codigo': self.codigo,
            'texto': self.texto,
            'contexto': self.contexto,
            'tipo': self.tipo,
            'opciones': self.opciones if incluir_clave else self._opciones_sin_clave(),
            'obligatorio': self.obligatorio,
            'orden': self.orden,
            'activo': self.activo,
            'version': self.version,
        }
