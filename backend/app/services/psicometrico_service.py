"""Motor de procesamiento psicométrico — Holland RIASEC con puntuación binaria."""

from ..extensions import db
from ..models.instrumento import Dimension, Escala, Item, item_de_intereses_autorizado
from ..models.aplicacion import Aplicacion, Respuesta
from ..models.resultado import ResultadoDimension, PerfilVocacional
from ..models.demografico import FormulaCalculo


# Descripciones de los 6 perfiles Holland RIASEC
PERFILES_HOLLAND = {
    'Realista': {
        'codigo': 'R',
        'descripcion': 'Tienes una fuerte inclinación hacia actividades prácticas, mecánicas y al aire libre. Disfrutas trabajar con las manos, herramientas y maquinaria. Prefieres resolver problemas de forma concreta y tangible.',
        'carreras_afines': 'Ingeniería Mecánica, Ingeniería Civil, Agricultura, Veterinaria, Mecatrónica, Electricidad, Deportes, Fuerzas Militares',
        'fortalezas': 'Habilidad manual, resistencia física, pensamiento práctico, coordinación motora',
        'ambiente': 'Talleres, laboratorios técnicos, trabajo de campo, construcción',
    },
    'Investigador': {
        'codigo': 'I',
        'descripcion': 'Posees una gran curiosidad intelectual y disfrutas investigar, analizar datos y resolver problemas complejos. Te motiva descubrir nuevos conocimientos y comprender fenómenos.',
        'carreras_afines': 'Medicina, Biología, Química, Física, Matemáticas, Ingeniería de Sistemas, Psicología, Investigación Científica',
        'fortalezas': 'Pensamiento analítico, curiosidad, capacidad de abstracción, meticulosidad',
        'ambiente': 'Laboratorios, centros de investigación, institutos científicos, bibliotecas',
    },
    'Artístico': {
        'codigo': 'A',
        'descripcion': 'Tienes gran sensibilidad creativa y necesitas expresarte a través del arte en sus diversas formas. Valoras la originalidad, la estética y la libertad de expresión.',
        'carreras_afines': 'Diseño Gráfico, Arquitectura, Artes Plásticas, Música, Literatura, Comunicación Social, Publicidad, Cine',
        'fortalezas': 'Creatividad, imaginación, sensibilidad estética, pensamiento divergente',
        'ambiente': 'Estudios de diseño, teatros, medios de comunicación, agencias creativas',
    },
    'Social': {
        'codigo': 'S',
        'descripcion': 'Te motiva profundamente ayudar a otros, enseñar y contribuir al bienestar de las personas. Tienes excelentes habilidades de comunicación y empatía.',
        'carreras_afines': 'Psicología, Trabajo Social, Educación, Enfermería, Medicina, Derecho, Terapia Ocupacional, Orientación',
        'fortalezas': 'Empatía, comunicación, liderazgo social, vocación de servicio, paciencia',
        'ambiente': 'Hospitales, escuelas, centros comunitarios, ONGs, instituciones educativas',
    },
    'Emprendedor': {
        'codigo': 'E',
        'descripcion': 'Tienes aptitudes para el liderazgo, la persuasión y la toma de decisiones. Te motiva alcanzar metas ambiciosas, influir en otros y generar impacto económico.',
        'carreras_afines': 'Administración de Empresas, Marketing, Economía, Negocios Internacionales, Derecho, Ciencias Políticas, Comunicación',
        'fortalezas': 'Liderazgo, persuasión, visión estratégica, toma de decisiones, iniciativa',
        'ambiente': 'Empresas, startups, organizaciones políticas, medios, firmas de consultoría',
    },
    'Convencional': {
        'codigo': 'C',
        'descripcion': 'Disfrutas de la organización, el orden y el trabajo con datos y procedimientos. Eres metódico/a, confiable y prefieres ambientes estructurados y predecibles.',
        'carreras_afines': 'Contaduría, Administración Financiera, Ingeniería Industrial, Archivística, Secretariado, Logística, Auditoría',
        'fortalezas': 'Organización, precisión, responsabilidad, atención al detalle, eficiencia',
        'ambiente': 'Oficinas corporativas, bancos, entidades gubernamentales, firmas contables',
    },
}


class PsicometricoService:
    """Motor de procesamiento psicométrico parametrizable — Holland RIASEC."""

    @staticmethod
    def obtener_formula_activa():
        """Obtener la fórmula de cálculo activa."""
        formula = FormulaCalculo.query.filter_by(activa=True).first()
        if formula:
            return formula.parametros
        return {
            'metodo': 'suma_binaria',
            'valor_positivo': 1,
            'valor_negativo': 0,
            'areas': ['Realista', 'Investigador', 'Artístico', 'Social', 'Emprendedor', 'Convencional'],
            'criterio_dominante': 'puntaje_maximo',
            'umbral_afinidad': 0.6,
        }

    @staticmethod
    def _es_interes(nombre_dimension) -> bool:
        return 'interes' in (nombre_dimension or '').lower()

    @staticmethod
    def _es_competencia(nombre_dimension) -> bool:
        return 'competencia' in (nombre_dimension or '').lower()

    @staticmethod
    def _obtener_aplicacion_complementaria(aplicacion):
        """Busca la aplicación completada más reciente del mismo estudiante para el
        instrumento complementario (Intereses <-> Competencias).

        En este sistema cada instrumento (Intereses / Competencias) se aplica por
        separado; el perfil integrado exige cruzar ambos, por lo que se busca la
        otra prueba ya completada por el mismo estudiante.
        """
        dimension_actual = aplicacion.configuracion.instrumento.dimensiones.first()
        nombre_actual = dimension_actual.nombre if dimension_actual else ''
        buscar_interes = PsicometricoService._es_competencia(nombre_actual)
        buscar_competencia = PsicometricoService._es_interes(nombre_actual)
        if not buscar_interes and not buscar_competencia:
            return None

        candidatas = Aplicacion.query.filter(
            Aplicacion.usuario_id == aplicacion.usuario_id,
            Aplicacion.estado == 'completada',
            Aplicacion.id != aplicacion.id,
        ).order_by(Aplicacion.fecha_fin.desc()).all()

        for otra in candidatas:
            dim_otra = otra.configuracion.instrumento.dimensiones.first()
            nombre_otra = dim_otra.nombre if dim_otra else ''
            if buscar_interes and PsicometricoService._es_interes(nombre_otra):
                return otra
            if buscar_competencia and PsicometricoService._es_competencia(nombre_otra):
                return otra
        return None

    @staticmethod
    def _maximo_item(item) -> float:
        """Puntaje máximo que un ítem puede aportar en una sola respuesta."""
        return 4 if item.tipo == 'juicio_situacional' else 1

    @staticmethod
    def _contribuciones_maximas(item) -> list:
        """Áreas RIASEC a las que aporta un ítem y su tope de puntaje, sin depender de la respuesta.

        - comparacion_binaria (Intereses): el ítem "toca" dos campos (A y B); cada uno
          tiene una oportunidad máxima de 1 punto (se gana si se elige ese lado).
        - juicio_situacional (Competencias): aporta hasta 4 puntos al campo de su escala.
        - tipos legados (eleccion_forzada / opcion_multiple binaria): aportan hasta 1 punto
          al campo de su escala.
        """
        if item.tipo == 'comparacion_binaria':
            ops = item.opciones or {}
            areas = []
            campo_a = (ops.get('opcion_a') or {}).get('campo')
            campo_b = (ops.get('opcion_b') or {}).get('campo')
            if campo_a:
                areas.append((campo_a, 1))
            if campo_b:
                areas.append((campo_b, 1))
            return areas

        area = item.escala.nombre if item.escala else None
        if not area:
            return []
        if item.tipo == 'juicio_situacional':
            return [(area, 4)]
        return [(area, 1)]

    @staticmethod
    def _contribuciones(item, r) -> list:
        """Puntos realmente obtenidos por área a partir de una respuesta concreta."""
        if r is None or r.valor is None:
            return []

        if item.tipo == 'comparacion_binaria':
            ops = item.opciones or {}
            campo_a = (ops.get('opcion_a') or {}).get('campo')
            campo_b = (ops.get('opcion_b') or {}).get('campo')
            try:
                elegido = int(r.valor)
            except (TypeError, ValueError):
                return []
            contrib = []
            if campo_a:
                contrib.append((campo_a, 1 if elegido == 0 else 0))
            if campo_b:
                contrib.append((campo_b, 1 if elegido == 1 else 0))
            return contrib

        area = item.escala.nombre if item.escala else None
        if not area:
            return []

        if item.tipo == 'juicio_situacional':
            opciones = (item.opciones or {}).get('opciones', [])
            try:
                idx = int(r.valor)
            except (TypeError, ValueError):
                return []
            if 0 <= idx < len(opciones) and isinstance(opciones[idx], dict):
                return [(area, opciones[idx].get('puntaje', 0))]
            return [(area, 0)]

        if item.tipo == 'opcion_multiple':
            ops = item.opciones
            opciones = ops.get('opciones', []) if isinstance(ops, dict) else (ops or [])
            try:
                idx = int(r.valor)
            except (TypeError, ValueError):
                return []
            positivo = 1 if (0 <= idx < len(opciones) and isinstance(opciones[idx], dict) and opciones[idx].get('valor') == 1) else 0
            return [(area, positivo)]

        # eleccion_forzada (legado): r.valor == 1 es positivo
        return [(area, 1 if r.valor == 1 else 0)]

    @staticmethod
    def calcular_puntajes_dimension(aplicacion_id: int) -> list:
        """Calcula puntajes brutos por dimensión (Intereses y Competencias)."""
        aplicacion = Aplicacion.query.get_or_404(aplicacion_id)
        instrumento = aplicacion.configuracion.instrumento

        resultados = []
        for dimension in instrumento.dimensiones.order_by(Dimension.orden):
            items_map = {}
            for escala in dimension.escalas:
                for item in escala.items.filter_by(activo=True):
                    items_map[item.id] = item

            if not items_map:
                continue

            respuestas_por_item = {
                r.item_id: r for r in Respuesta.query.filter(
                    Respuesta.aplicacion_id == aplicacion_id,
                    Respuesta.item_id.in_(list(items_map.keys()))
                ).all()
            }

            if not respuestas_por_item:
                continue

            puntaje_bruto = 0
            for item_id, r in respuestas_por_item.items():
                item = items_map.get(item_id)
                if not item:
                    continue
                puntaje_bruto += sum(p for _area, p in PsicometricoService._contribuciones(item, r))

            maximo_posible = sum(PsicometricoService._maximo_item(item) for item in items_map.values())
            puntaje_normalizado = (puntaje_bruto / maximo_posible * 100) if maximo_posible > 0 else 0

            if puntaje_normalizado >= 80:
                nivel = 'muy_alto'
            elif puntaje_normalizado >= 60:
                nivel = 'alto'
            elif puntaje_normalizado >= 40:
                nivel = 'medio'
            else:
                nivel = 'bajo'

            resultado = ResultadoDimension.query.filter_by(
                aplicacion_id=aplicacion_id,
                dimension_id=dimension.id
            ).first()

            if resultado:
                resultado.puntaje_bruto = puntaje_bruto
                resultado.puntaje_normalizado = round(puntaje_normalizado, 2)
                resultado.nivel = nivel
            else:
                resultado = ResultadoDimension(
                    aplicacion_id=aplicacion_id,
                    dimension_id=dimension.id,
                    puntaje_bruto=puntaje_bruto,
                    puntaje_normalizado=round(puntaje_normalizado, 2),
                    nivel=nivel,
                )
                db.session.add(resultado)

            resultados.append(resultado)

        db.session.commit()
        return resultados

    @staticmethod
    def calcular_puntajes_escala(aplicacion_id: int) -> dict:
        """Calcula puntajes por campo RIASEC (R-I-A-S-E-C), separado por dimensión.

        A diferencia del diseño anterior (ítem → una sola escala), los ítems de
        comparación binaria (Intereses) pueden aportar puntaje a dos campos distintos
        según cuál opción elija el estudiante, por lo que el cálculo se hace agregando
        por (dimensión, campo) en lugar de por la simple relación item→escala.
        """
        aplicacion = Aplicacion.query.get_or_404(aplicacion_id)
        instrumento = aplicacion.configuracion.instrumento

        items_map = {}
        dimension_de_item = {}
        for dimension in instrumento.dimensiones:
            for escala in dimension.escalas:
                for item in escala.items.filter_by(activo=True):
                    items_map[item.id] = item
                    dimension_de_item[item.id] = dimension

        respuestas_por_item = {
            r.item_id: r for r in Respuesta.query.filter(
                Respuesta.aplicacion_id == aplicacion_id,
                Respuesta.item_id.in_(list(items_map.keys()))
            ).all()
        }

        acumulado = {}

        def _bucket(dimension_id, area):
            return acumulado.setdefault((dimension_id, area), {
                'puntaje': 0, 'maximo': 0, 'items_totales': 0,
                'respondidos': 0, 'respuestas_positivas': 0,
            })

        for item_id, item in items_map.items():
            dimension = dimension_de_item[item_id]
            for area, maximo in PsicometricoService._contribuciones_maximas(item):
                b = _bucket(dimension.id, area)
                b['maximo'] += maximo
                b['items_totales'] += 1

            r = respuestas_por_item.get(item_id)
            if r is None or r.valor is None:
                continue
            for area, puntos in PsicometricoService._contribuciones(item, r):
                b = _bucket(dimension.id, area)
                b['puntaje'] += puntos
                b['respondidos'] += 1
                if puntos > 0:
                    b['respuestas_positivas'] += 1

        resultados_escala = {}
        for dimension in instrumento.dimensiones:
            for escala in dimension.escalas:
                datos = acumulado.get((dimension.id, escala.nombre), {
                    'puntaje': 0, 'maximo': 0, 'items_totales': 0, 'respondidos': 0, 'respuestas_positivas': 0,
                })
                normalizado = (datos['puntaje'] / datos['maximo'] * 100) if datos['maximo'] > 0 else 0

                clave = f"{escala.nombre} ({dimension.nombre})"
                resultados_escala[clave] = {
                    'escala_id': escala.id,
                    'escala_nombre': escala.nombre,
                    'dimension': dimension.nombre,
                    'puntaje_bruto': datos['puntaje'],
                    'puntaje_maximo': datos['maximo'],
                    'puntaje_normalizado': round(normalizado, 2),
                    'total_items': datos['items_totales'],
                    'respondidos': datos['respondidos'],
                    'respuestas_positivas': datos['respuestas_positivas'],
                }

        return resultados_escala

    @staticmethod
    def generar_perfil(aplicacion_id: int) -> PerfilVocacional:
        """Genera el perfil vocacional Holland RIASEC basado en árbol de decisión binario.

        Como Intereses y Competencias son instrumentos separados (cada uno se aplica
        de forma independiente), el perfil integrado cruza los resultados de la
        aplicación actual con los de la prueba complementaria más reciente que el
        mismo estudiante haya completado (si existe).
        """
        puntajes_escala = PsicometricoService.calcular_puntajes_escala(aplicacion_id)
        resultados_dim = PsicometricoService.calcular_puntajes_dimension(aplicacion_id)

        aplicacion = Aplicacion.query.get_or_404(aplicacion_id)
        aplicacion_complementaria = PsicometricoService._obtener_aplicacion_complementaria(aplicacion)
        puntajes_escala_todas = dict(puntajes_escala)
        if aplicacion_complementaria:
            puntajes_escala_todas.update(
                PsicometricoService.calcular_puntajes_escala(aplicacion_complementaria.id)
            )

        formula = PsicometricoService.obtener_formula_activa()
        areas_holland = formula.get('areas', ['Realista', 'Investigador', 'Artístico', 'Social', 'Emprendedor', 'Convencional'])

        # Combinar puntajes de ambas dimensiones (Intereses + Competencias) por área
        puntajes_por_area = {}
        for area in areas_holland:
            escalas_area = {k: v for k, v in puntajes_escala_todas.items() if v.get('escala_nombre') == area}
            interes = next((v for v in escalas_area.values() if PsicometricoService._es_interes(v['dimension'])), None)
            competencia = next((v for v in escalas_area.values() if PsicometricoService._es_competencia(v['dimension'])), None)

            interes_normalizado = interes['puntaje_normalizado'] if interes else 0
            competencia_normalizado = competencia['puntaje_normalizado'] if competencia else 0
            normalizado = round((interes_normalizado + competencia_normalizado) / 2, 2) if (interes or competencia) else 0

            total_positivas = (interes['respuestas_positivas'] if interes else 0) + (competencia['respuestas_positivas'] if competencia else 0)
            total_items = (interes['total_items'] if interes else 0) + (competencia['total_items'] if competencia else 0)

            puntajes_por_area[area] = {
                'positivas': total_positivas,
                'total': total_items,
                'normalizado': normalizado,
                'Intereses': interes['puntaje_bruto'] if interes else 0,
                'Competencias': competencia['puntaje_bruto'] if competencia else 0,
                # Campos requeridos por los lineamientos de la simulación: ranking de
                # intereses cruzado con el porcentaje de competencias por campo.
                'interes_puntaje': interes['puntaje_bruto'] if interes else 0,
                'interes_normalizado': interes_normalizado,
                'competencia_puntaje': competencia['puntaje_bruto'] if competencia else 0,
                'competencia_porcentaje': competencia_normalizado,
            }

        # ── Enriquecer con PLN si hay respuestas abiertas ──────────────────
        try:
            from .pln_service import PlnService
            pln_resultado = PlnService.analizar_aplicacion(aplicacion_id)
            pln_scores = pln_resultado.get('scores_agregados', {})
            n_pln = pln_resultado.get('n_respuestas_analizadas', 0)
            if n_pln > 0 and pln_scores:
                puntajes_ajustados = PlnService.ajustar_perfil_con_pln(
                    {area: datos for area, datos in puntajes_por_area.items()},
                    pln_scores,
                    peso_pln=0.15,
                )
                # Actualizar normalizado en puntajes_por_area con ajuste PLN
                for area in puntajes_por_area:
                    if area in puntajes_ajustados:
                        puntajes_por_area[area]['normalizado'] = puntajes_ajustados[area]
                        puntajes_por_area[area]['pln_score'] = pln_scores.get(area, 0)
                        puntajes_por_area[area]['pln_ajustado'] = True
        except Exception:
            pass  # PLN es un enriquecimiento opcional; no bloquear el cálculo principal

        # Determinar perfil dominante: se cruza el ranking de INTERESES (criterio primario,
        # según los lineamientos de la simulación) con el porcentaje de COMPETENCIAS por campo.
        if puntajes_por_area:
            ranking_intereses = sorted(areas_holland, key=lambda a: puntajes_por_area[a]['interes_puntaje'], reverse=True)
            for posicion, area in enumerate(ranking_intereses, start=1):
                puntajes_por_area[area]['ranking_interes'] = posicion

            perfil_principal_nombre = ranking_intereses[0]
            perfil_secundario_nombre = ranking_intereses[1] if len(ranking_intereses) > 1 else None
            campo_prioritario_3 = ranking_intereses[2] if len(ranking_intereses) > 2 else None

            codigo_riasec = ''.join(
                PERFILES_HOLLAND.get(a, {}).get('codigo', '?')
                for a in ranking_intereses[:3]
            )
        else:
            ranking_intereses = []
            perfil_principal_nombre = 'Sin determinar'
            perfil_secundario_nombre = None
            campo_prioritario_3 = None
            codigo_riasec = '---'

        info_perfil = PERFILES_HOLLAND.get(perfil_principal_nombre, {})

        # Generar fortalezas
        umbral = formula.get('umbral_afinidad', 0.6) * 100
        fortalezas_list = []
        for area, datos in sorted(puntajes_por_area.items(), key=lambda x: x[1]['normalizado'], reverse=True):
            if datos['normalizado'] >= umbral:
                info = PERFILES_HOLLAND.get(area, {})
                fortalezas_list.append(f"• {area} ({datos['normalizado']:.0f}%): {info.get('fortalezas', '')}")

        # Áreas de desarrollo
        areas_desarrollo_list = []
        for area, datos in sorted(puntajes_por_area.items(), key=lambda x: x[1]['normalizado']):
            if datos['normalizado'] < umbral:
                areas_desarrollo_list.append(f"• {area} ({datos['normalizado']:.0f}%): oportunidad de exploración")

        # Recomendaciones
        recomendaciones_list = [
            f"Tu perfil vocacional Holland es: {perfil_principal_nombre} (Código RIASEC: {codigo_riasec}).",
            info_perfil.get('descripcion', ''),
        ]
        if info_perfil.get('carreras_afines'):
            recomendaciones_list.append(f"Carreras afines a tu perfil: {info_perfil['carreras_afines']}.")
        if perfil_secundario_nombre:
            info_sec = PERFILES_HOLLAND.get(perfil_secundario_nombre, {})
            recomendaciones_list.append(
                f"Tu perfil secundario es {perfil_secundario_nombre}. También podrías explorar: {info_sec.get('carreras_afines', '')}."
            )
        if info_perfil.get('ambiente'):
            recomendaciones_list.append(f"Ambientes de trabajo ideales: {info_perfil['ambiente']}.")
        recomendaciones_list.append(
            "Se recomienda hablar con el orientador escolar o consejero de tu institución para una orientación vocacional personalizada."
        )
        if not aplicacion_complementaria:
            nombre_pendiente = 'Competencias' if PsicometricoService._es_interes(
                aplicacion.configuracion.instrumento.dimensiones.first().nombre
            ) else 'Intereses'
            recomendaciones_list.append(
                f"Aún no has completado la prueba de {nombre_pendiente}; tu perfil integrado se actualizará cuando la realices."
            )

        # Interpretación preliminar y orientativa que cruza ranking de intereses + % de competencias
        competencia_pct_principal = puntajes_por_area.get(perfil_principal_nombre, {}).get('competencia_porcentaje', 0)
        interpretacion_generada = (
            f"Perfil preliminar y orientativo (versión de simulación). Tu campo de interés prioritario es "
            f"{perfil_principal_nombre} (1º lugar)"
            + (f", seguido de {perfil_secundario_nombre} (2º)" if perfil_secundario_nombre else "")
            + (f" y {campo_prioritario_3} (3º)" if campo_prioritario_3 else "")
            + f". Tu porcentaje de competencias en {perfil_principal_nombre} es de {competencia_pct_principal:.0f}%. "
            "Este resultado busca validar la claridad, el funcionamiento y la utilidad inicial del instrumento, "
            "por lo que debe interpretarse de forma preliminar."
        )

        # Advertencia si no completó
        total_posibles = sum(d.get('total', 0) for d in puntajes_por_area.values())
        respondidas_reales = sum(e.get('respondidos', 0) for e in puntajes_escala.values())
        if respondidas_reales < total_posibles:
            recomendaciones_list.insert(0,
                f"⚠️ ADVERTENCIA: No completaste todas las preguntas ({respondidas_reales}/{total_posibles}). Los resultados pueden no ser completamente representativos."
            )

        # Guardar o actualizar perfil
        perfil = PerfilVocacional.query.filter_by(aplicacion_id=aplicacion_id).first()
        perfil_data = {
            'perfil_principal': perfil_principal_nombre,
            'perfil_secundario': perfil_secundario_nombre,
            'descripcion': info_perfil.get('descripcion', ''),
            'fortalezas': '\n'.join(fortalezas_list) if fortalezas_list else 'No se identificaron fortalezas destacadas aún.',
            'areas_desarrollo': '\n'.join(areas_desarrollo_list) if areas_desarrollo_list else 'Sin áreas de desarrollo identificadas.',
            'recomendaciones': '\n'.join(recomendaciones_list),
            'datos_json': {
                'puntajes_escala': puntajes_escala_todas,
                'puntajes_por_area': puntajes_por_area,
                'codigo_riasec': codigo_riasec,
                'ranking_intereses': ranking_intereses,
                'campo_prioritario_1': perfil_principal_nombre,
                'campo_prioritario_2': perfil_secundario_nombre,
                'campo_prioritario_3': campo_prioritario_3,
                'interpretacion_generada': interpretacion_generada,
                'carreras_afines': [c.strip() for c in info_perfil.get('carreras_afines', '').split(',') if c.strip()],
                'ambiente_trabajo': info_perfil.get('ambiente', ''),
                'resultados_dimension': [r.to_dict() for r in resultados_dim],
                'formula_utilizada': formula,
                'advertencia': (
                    f'No completaste todas las preguntas ({respondidas_reales}/{total_posibles}). Los resultados pueden no ser completamente representativos.'
                    if respondidas_reales < total_posibles else None
                ),
            },
        }

        if perfil:
            for key, value in perfil_data.items():
                setattr(perfil, key, value)
        else:
            perfil = PerfilVocacional(aplicacion_id=aplicacion_id, **perfil_data)
            db.session.add(perfil)

        db.session.commit()
        return perfil
