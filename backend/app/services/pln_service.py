"""
Servicio de Procesamiento de Lenguaje Natural (PLN) para respuestas abiertas.

Implementación sin dependencias externas de modelos descargables:
- Preprocesamiento: normalización, eliminación de stopwords en español
- Clasificación por diccionario RIASEC extenso en español colombiano
- Ajuste de puntajes RIASEC basado en texto libre
- Análisis de sentimiento simple (positivo / negativo / neutro)

Uso principal: enriquecer el perfil vocacional cuando el instrumento
incluye ítems de tipo 'abierta'.
"""

import re
import unicodedata
from ..extensions import db
from ..models.aplicacion import Respuesta
from ..models.ml_models import PlnAnalisis

# ─────────────────────────────────────────────────────────────────────────────
# Diccionario de palabras clave RIASEC en español
# ─────────────────────────────────────────────────────────────────────────────
KEYWORDS_RIASEC = {
    'Realista': [
        # Actividades manuales y técnicas
        'herramienta', 'maquina', 'motor', 'mecanica', 'construccion', 'madera', 'metal',
        'taller', 'campo', 'agricultura', 'ganado', 'animales', 'deporte', 'fisico', 'manual',
        'reparar', 'construir', 'manejar', 'operar', 'tierra', 'planta', 'cultivo',
        'automovil', 'carro', 'moto', 'electrico', 'plomeria', 'soldadura', 'carpinteria',
        'militar', 'policia', 'mecanico', 'tecnico', 'industrial', 'practico', 'concreto',
        'electricidad', 'electronica', 'maquinaria', 'equipo', 'arreglar', 'fabricar',
        'albanileria', 'obra', 'entrenamiento', 'atletismo', 'natacion', 'futbol', 'ejercicio',
        'torno', 'soldador', 'electricista', 'fontanero', 'ferreteria', 'bodega', 'almacen',
        'granja', 'finca', 'campo', 'jardin', 'pesca', 'caza', 'forestal', 'mineria',
        'bombero', 'rescate', 'outdoor', 'aventura', 'caminar', 'escalar', 'montar',
        'robot', 'automatizacion', 'cnc', 'soldaduras', 'estructuras', 'puentes',
    ],
    'Investigador': [
        # Ciencia, análisis, investigación
        'investigar', 'ciencia', 'laboratorio', 'experimento', 'analisis', 'datos',
        'quimica', 'fisica', 'biologia', 'matematicas', 'estadistica', 'investigacion',
        'descubrir', 'hipotesis', 'teoria', 'formula', 'calculo', 'microscopio',
        'leer', 'libro', 'estudio', 'aprender', 'conocimiento', 'inteligencia',
        'medicina', 'doctor', 'hospital', 'diagnostico', 'sintoma', 'tratamiento',
        'tecnologia', 'programar', 'codigo', 'algoritmo', 'software', 'computadora',
        'resolver', 'problema', 'logica', 'razonamiento', 'numero', 'ecuacion',
        'astronomia', 'geologia', 'ecologia', 'botanica', 'zoologia', 'genetica',
        'analizar', 'comprender', 'estudiar', 'explorar', 'observar', 'medir',
        'base de datos', 'inteligencia artificial', 'machine learning', 'big data',
        'neurociencia', 'bioquimica', 'farmacia', 'veterinaria', 'biotecnologia',
        'matematico', 'cientifico', 'ingeniero', 'analista', 'investigador',
        'publicacion', 'articulo', 'tesis', 'doctorado', 'maestria', 'postgrado',
        'laboratorista', 'quimico', 'biologo', 'fisico', 'astrónomo', 'geologo',
    ],
    'Artístico': [
        # Arte, creatividad, expresión
        'arte', 'pintura', 'dibujo', 'diseno', 'musica', 'teatro', 'danza', 'baile',
        'escritura', 'poesia', 'literatura', 'novela', 'cuento', 'pelicula', 'cine',
        'fotografia', 'escultura', 'moda', 'decoracion', 'arquitectura', 'publicidad',
        'creativo', 'creatividad', 'imaginacion', 'expresion', 'sentimiento', 'emocion',
        'cantar', 'actuar', 'dibujar', 'pintar', 'crear', 'disenar', 'decorar',
        'instrumento', 'guitarra', 'piano', 'violin', 'percusion', 'coro', 'banda',
        'espectaculo', 'escenario', 'galeria', 'museo', 'exposicion', 'artista',
        'comunicacion', 'periodismo', 'television', 'radio', 'redes sociales', 'contenido',
        'estetica', 'belleza', 'color', 'forma', 'estilo', 'maquillaje', 'fotografiar',
        'videojuego', 'animacion', 'ilustracion', 'comic', 'manga', 'graffiti',
        'bailarin', 'cantante', 'musico', 'actor', 'cineasta', 'escritor', 'poeta',
        'grafitero', 'tatuador', 'ceramica', 'joyeria', 'textil', 'tejido', 'bordado',
        'chef', 'gastronomia', 'culinaria', 'reposteria', 'cocina creativa',
        'influencer', 'youtuber', 'streamer', 'podcast', 'blog', 'vlog',
    ],
    'Social': [
        # Ayuda, enseñanza, trabajo comunitario
        'ayudar', 'personas', 'comunidad', 'servicio', 'voluntario', 'solidaridad',
        'ensenar', 'educacion', 'escuela', 'ninos', 'jovenes', 'familia', 'padres',
        'psicologia', 'consejeria', 'terapia', 'bienestar', 'salud mental', 'apoyo',
        'enfermeria', 'medico', 'cuidar', 'paciente', 'cuidado', 'atencion',
        'trabajo social', 'barrio', 'programa', 'proyecto social', 'fundacion',
        'hablar', 'comunicar', 'escuchar', 'empatia', 'comprension', 'tolerancia',
        'liderazgo', 'grupo', 'equipo', 'colaborar', 'cooperar', 'participar',
        'religion', 'iglesia', 'pastoral', 'fe', 'espiritualidad', 'mision',
        'derechos', 'justicia', 'igualdad', 'paz', 'reconciliacion', 'mediacion',
        'orientacion', 'guiar', 'mentor', 'tutor', 'coaching', 'acompanar',
        'humanidades', 'sociologia', 'antropologia', 'trabajo comunitario',
        'defensor', 'activismo', 'ong', 'organizacion', 'liderar', 'inspirar',
        'profesor', 'docente', 'maestro', 'pedagogo', 'educador', 'formador',
        'terapeuta', 'consejero', 'psicologo', 'trabajador social', 'enfermero',
    ],
    'Emprendedor': [
        # Negocios, liderazgo, persuasión
        'negocio', 'empresa', 'dinero', 'economia', 'ventas', 'comercio', 'mercado',
        'emprender', 'empresario', 'gerente', 'administracion', 'gestion', 'direccion',
        'liderazgo', 'jefe', 'organizar', 'planear', 'estrategia', 'objetivos',
        'politica', 'gobierno', 'abogado', 'derecho', 'ley', 'justicia', 'poder',
        'convencer', 'persuadir', 'negociar', 'vender', 'marketing', 'publicidad',
        'inversion', 'finanzas', 'banco', 'rentabilidad', 'ganancias', 'utilidades',
        'startup', 'innovar', 'proyecto', 'emprendimiento', 'idea de negocio',
        'ganar', 'competir', 'triunfar', 'exito', 'metas', 'ambicion', 'crecer',
        'internacional', 'importar', 'exportar', 'global', 'viajes', 'idiomas',
        'cliente', 'proveedor', 'contrato', 'propuesta', 'presentacion', 'reunion',
        'influenciar', 'impacto', 'cambio', 'transformar', 'liderar', 'dirigir',
        'comerciante', 'vendedor', 'representante', 'consultor', 'asesor',
        'alcalde', 'congresista', 'gobernador', 'diplomacia', 'relaciones',
        'ceo', 'director', 'fundador', 'socio', 'accionista', 'inversor',
    ],
    'Convencional': [
        # Orden, datos, procedimientos
        'organizar', 'orden', 'clasificar', 'archivar', 'registro', 'documentos',
        'contabilidad', 'cuentas', 'presupuesto', 'factura', 'balance', 'impuesto',
        'oficina', 'computadora', 'excel', 'hoja de calculo', 'base de datos',
        'seguir', 'reglas', 'normas', 'procedimientos', 'manual', 'protocolo',
        'exactitud', 'precision', 'detalle', 'minucioso', 'cuidadoso', 'metodico',
        'secretaria', 'recepcion', 'asistente', 'administrativo', 'logistica',
        'inventario', 'control', 'supervisar', 'revisar', 'auditoria', 'revision',
        'reportes', 'estadisticas', 'informe', 'tramites', 'diligencias',
        'bancario', 'cajero', 'transacciones', 'pagos', 'cobros', 'nomina',
        'planilla', 'formularios', 'gestion documental', 'archivo', 'carpeta',
        'sistematico', 'ordenado', 'puntual', 'responsable', 'comprometido',
        'contador', 'auditor', 'tesorero', 'pagador', 'recepcionista', 'secretario',
        'analista de datos', 'digitador', 'capturador', 'procesador', 'registrador',
        'cronograma', 'calendario', 'agenda', 'planificacion', 'seguimiento',
    ],
}

# Stopwords básicas en español
STOPWORDS_ES = {
    'a', 'al', 'algo', 'algunas', 'algunos', 'ante', 'antes', 'como', 'con', 'contra',
    'cual', 'cuando', 'de', 'del', 'desde', 'donde', 'durante', 'e', 'el', 'ella',
    'ellas', 'ellos', 'en', 'entre', 'era', 'eras', 'eramos', 'eran', 'eres', 'es',
    'esa', 'esas', 'ese', 'eso', 'esos', 'esta', 'estaba', 'estado', 'estar', 'este',
    'esto', 'estos', 'fue', 'fueron', 'fui', 'gusto', 'ha', 'hace', 'hacen', 'hacer',
    'hacia', 'han', 'hay', 'he', 'hemos', 'his', 'i', 'igual', 'la', 'las', 'le',
    'les', 'lo', 'los', 'me', 'mi', 'mia', 'mis', 'mismo', 'mucho', 'muy', 'ni',
    'no', 'nos', 'o', 'otra', 'otras', 'otro', 'otros', 'para', 'pero', 'poco', 'por',
    'porque', 'que', 'quien', 'quienes', 'se', 'ser', 'si', 'sin', 'sobre', 'su',
    'sus', 'tambien', 'tanto', 'te', 'tengo', 'ti', 'todo', 'todos', 'tu', 'tus', 'un',
    'una', 'unas', 'unos', 'usted', 'ustedes', 'vos', 'y', 'ya', 'yo',
}

# Palabras de sentimiento positivo/negativo
POSITIVAS = {'me gusta', 'disfruto', 'amo', 'adoro', 'me encanta', 'me apasiona',
             'me interesa', 'quiero', 'deseo', 'sueno', 'aspiro', 'feliz', 'alegre',
             'entusiasmo', 'emocion', 'motivado', 'apasionado', 'gusto', 'placer'}
NEGATIVAS = {'no me gusta', 'odio', 'detesto', 'no quiero', 'aburrido', 'fastidio',
             'no me interesa', 'nunca', 'jamas', 'rechazo', 'evito', 'dificulto'}


class PlnService:

    @staticmethod
    def _normalizar(texto: str) -> str:
        """Convierte a minúsculas y elimina acentos."""
        texto = texto.lower().strip()
        texto = unicodedata.normalize('NFD', texto)
        texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
        return texto

    @staticmethod
    def _tokenizar(texto: str) -> list:
        """Divide el texto en tokens alfanuméricos."""
        tokens = re.findall(r'\b[a-z]{3,}\b', texto)
        return [t for t in tokens if t not in STOPWORDS_ES]

    @staticmethod
    def _detectar_sentimiento(texto: str) -> str:
        """Retorna 'positivo', 'negativo' o 'neutro' para el texto."""
        for frase in NEGATIVAS:
            if frase in texto:
                return 'negativo'
        for frase in POSITIVAS:
            if frase in texto:
                return 'positivo'
        return 'neutro'

    @staticmethod
    def analizar_texto(texto: str) -> dict:
        """
        Analiza un texto libre y retorna scores RIASEC (0-100),
        palabras clave encontradas, área dominante y confianza.
        """
        if not texto or not texto.strip():
            return {
                'scores_riasec': {area: 0.0 for area in KEYWORDS_RIASEC},
                'palabras_clave': {},
                'area_dominante': None,
                'confianza': 0.0,
                'sentimiento': 'neutro',
            }

        texto_norm = PlnService._normalizar(texto)
        tokens = PlnService._tokenizar(texto_norm)
        sentimiento = PlnService._detectar_sentimiento(texto_norm)

        # Contar coincidencias por área
        coincidencias = {}
        palabras_encontradas = {}
        for area, keywords in KEYWORDS_RIASEC.items():
            matches = []
            for kw in keywords:
                kw_norm = PlnService._normalizar(kw)
                # Buscar keyword completa en texto normalizado
                if kw_norm in texto_norm:
                    matches.append(kw)
                elif any(tok.startswith(kw_norm[:5]) for tok in tokens if len(kw_norm) >= 5):
                    # Coincidencia parcial por raíz (stemming simple)
                    matches.append(kw)
            coincidencias[area] = len(set(matches))
            palabras_encontradas[area] = list(set(matches))

        total_matches = sum(coincidencias.values())

        # Calcular scores normalizados 0-100
        if total_matches == 0:
            scores = {area: 0.0 for area in KEYWORDS_RIASEC}
            area_dominante = None
            confianza = 0.0
        else:
            scores = {
                area: round(coincidencias[area] / total_matches * 100, 2)
                for area in KEYWORDS_RIASEC
            }

            # Si sentimiento negativo, reducir los scores a la mitad
            if sentimiento == 'negativo':
                scores = {area: round(v * 0.3, 2) for area, v in scores.items()}

            area_dominante = max(scores, key=lambda a: scores[a])
            max_score = scores[area_dominante]
            segundo_max = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0

            # Confianza: qué tan diferenciado está el área dominante
            confianza = round(min(1.0, (max_score - segundo_max) / 100 + 0.3), 4) if max_score > 0 else 0.0

        return {
            'scores_riasec': scores,
            'palabras_clave': palabras_encontradas,
            'area_dominante': area_dominante,
            'confianza': confianza,
            'sentimiento': sentimiento,
        }

    @staticmethod
    def analizar_respuesta(respuesta_id: int) -> dict:
        """
        Analiza el texto de una respuesta abierta, persiste el resultado
        en pln_analisis y retorna el dict.
        """
        respuesta = Respuesta.query.get_or_404(respuesta_id)
        texto = respuesta.valor_texto or ''
        resultado = PlnService.analizar_texto(texto)

        # Upsert en pln_analisis
        analisis = PlnAnalisis.query.filter_by(respuesta_id=respuesta_id).first()
        if not analisis:
            analisis = PlnAnalisis(respuesta_id=respuesta_id)
            db.session.add(analisis)

        analisis.texto_original = texto
        analisis.texto_procesado = PlnService._normalizar(texto)
        analisis.palabras_clave = resultado['palabras_clave']
        analisis.scores_riasec = resultado['scores_riasec']
        analisis.area_dominante = resultado['area_dominante']
        analisis.confianza = resultado['confianza']
        db.session.commit()

        return analisis.to_dict()

    @staticmethod
    def analizar_aplicacion(aplicacion_id: int) -> dict:
        """
        Analiza todas las respuestas abiertas de una aplicación.
        Retorna scores RIASEC agregados de las respuestas abiertas.
        """
        respuestas_abiertas = (
            Respuesta.query
            .filter_by(aplicacion_id=aplicacion_id)
            .join(Respuesta.item)
            .filter_by(tipo='abierta')
            .all()
        )

        if not respuestas_abiertas:
            return {
                'scores_agregados': {area: 0.0 for area in KEYWORDS_RIASEC},
                'n_respuestas_analizadas': 0,
                'areas_mencionadas': [],
            }

        scores_acumulados = {area: 0.0 for area in KEYWORDS_RIASEC}
        n_analizadas = 0
        areas_con_menciones = set()

        for resp in respuestas_abiertas:
            if not resp.valor_texto:
                continue
            resultado = PlnService.analizar_texto(resp.valor_texto)
            for area, score in resultado['scores_riasec'].items():
                scores_acumulados[area] += score
            if resultado['area_dominante']:
                areas_con_menciones.add(resultado['area_dominante'])
            n_analizadas += 1

        # Normalizar scores agregados al rango 0-100
        max_acum = max(scores_acumulados.values()) if scores_acumulados else 1
        if max_acum > 0:
            scores_norm = {
                area: round(v / max_acum * 100, 2)
                for area, v in scores_acumulados.items()
            }
        else:
            scores_norm = scores_acumulados

        return {
            'scores_agregados': scores_norm,
            'n_respuestas_analizadas': n_analizadas,
            'areas_mencionadas': sorted(areas_con_menciones),
        }

    @staticmethod
    def ajustar_perfil_con_pln(puntajes_por_area: dict, pln_scores: dict, peso_pln: float = 0.15) -> dict:
        """
        Combina los puntajes RIASEC de la escala cuantitativa con los scores
        del análisis PLN. El PLN aporta un máximo de `peso_pln` (15% por defecto).

        puntajes_por_area: dict area → normalizado (0-100)
        pln_scores: dict area → score (0-100) del análisis de texto
        Retorna nuevo dict de puntajes ajustados.
        """
        ajustados = {}
        for area in KEYWORDS_RIASEC:
            base = puntajes_por_area.get(area, {})
            if isinstance(base, dict):
                base_val = base.get('normalizado', 0.0)
            else:
                base_val = float(base)
            pln_val = pln_scores.get(area, 0.0)
            ajustado = base_val * (1 - peso_pln) + pln_val * peso_pln
            ajustados[area] = round(ajustado, 2)
        return ajustados
