"""Servicio de estadísticas agregadas para el dashboard institucional."""

from sqlalchemy import func, case
from ..extensions import db
from ..models.usuario import Usuario
from ..models.institucional import Institucion, Grado
from ..models.aplicacion import Aplicacion, ConfiguracionAplicacion
from ..models.resultado import ResultadoDimension, PerfilVocacional
from ..models.instrumento import Instrumento, Dimension, Escala
from ..models.demografico import DatoDemografico, CampoDemografico

RIASEC_AREAS = ['Realista', 'Investigador', 'Artístico', 'Social', 'Emprendedor', 'Convencional']



class EstadisticaService:
    """Servicio para cálculos estadísticos agregados."""

    @staticmethod
    def estadisticas_por_grado_area() -> list:
        """Devuelve para cada grado y área vocacional: promedio, mediana y desviación estándar de puntajes."""
        from sqlalchemy import cast, Float
        import numpy as np
        # Obtener campo grado
        campo_grado = CampoDemografico.query.filter_by(nombre='grado_escolar').first()
        if not campo_grado:
            return []
        # Query: grado, area, puntaje
        query = (
            db.session.query(
                DatoDemografico.valor.label('grado'),
                PerfilVocacional.perfil_principal.label('area'),
                ResultadoDimension.puntaje_normalizado.label('puntaje')
            )
            .join(Usuario, DatoDemografico.usuario_id == Usuario.id)
            .join(Aplicacion, Aplicacion.usuario_id == Usuario.id)
            .join(PerfilVocacional, PerfilVocacional.aplicacion_id == Aplicacion.id)
            .join(ResultadoDimension, ResultadoDimension.aplicacion_id == Aplicacion.id)
            .filter(DatoDemografico.campo_id == campo_grado.id)
            .filter(Aplicacion.estado == 'completada')
            .filter(ResultadoDimension.puntaje_normalizado != None)
        )
        resultados = query.all()
        # Agrupar por grado y área
        datos = {}
        for r in resultados:
            grado = str(r.grado).strip() if r.grado else 'Desconocido'
            area = r.area if r.area else 'Sin área'
            key = (grado, area)
            if key not in datos:
                datos[key] = []
            try:
                datos[key].append(float(r.puntaje))
            except Exception:
                continue
        # Calcular estadísticas
        estadisticas = []
        for (grado, area), puntajes in datos.items():
            if not puntajes:
                continue
            arr = np.array(puntajes)
            promedio = float(np.mean(arr))
            mediana = float(np.median(arr))
            std = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
            estadisticas.append({
                'grado': grado,
                'area': area,
                'promedio': round(promedio, 2),
                'mediana': round(mediana, 2),
                'desviacion': round(std, 2),
                'n': len(arr)
            })
        return estadisticas

    @staticmethod
    def estadisticas_participacion(configuracion_id: int = None) -> dict:
        """Estadísticas de participación en las pruebas (1 sola query con CASE)."""
        query = db.session.query(
            func.count(Aplicacion.id).label('total'),
            func.count(case((Aplicacion.estado == 'completada', 1))).label('completadas'),
            func.count(case((Aplicacion.estado == 'en_progreso', 1))).label('en_progreso'),
            func.count(case((Aplicacion.estado == 'abandonada', 1))).label('abandonadas'),
        )
        if configuracion_id:
            query = query.filter(Aplicacion.configuracion_id == configuracion_id)

        row = query.first()
        total     = row.total      if row else 0
        completadas = row.completadas if row else 0

        return {
            'total_aplicaciones': total,
            'completadas': completadas,
            'en_progreso': row.en_progreso if row else 0,
            'abandonadas': row.abandonadas if row else 0,
            'tasa_completacion': round(completadas / total * 100, 2) if total > 0 else 0,
        }

    @staticmethod
    def distribucion_perfiles(configuracion_id: int = None) -> list:
        """Distribución de perfiles vocacionales."""
        query = db.session.query(
            PerfilVocacional.perfil_principal,
            func.count(PerfilVocacional.id).label('cantidad')
        )

        if configuracion_id:
            query = query.join(Aplicacion).filter(
                Aplicacion.configuracion_id == configuracion_id
            )

        resultados = query.group_by(PerfilVocacional.perfil_principal).all()
        total = sum(r.cantidad for r in resultados)

        return [
            {
                'perfil': r.perfil_principal,
                'cantidad': r.cantidad,
                'porcentaje': round(r.cantidad / total * 100, 2) if total > 0 else 0,
            }
            for r in resultados
        ]

    @staticmethod
    def estadisticas_por_grado(configuracion_id: int = None) -> list:
        """Estadísticas de perfiles por grado escolar (usando campos demográficos dinámicos)."""
        from sqlalchemy.orm import aliased
        
        campo_grado = CampoDemografico.query.filter_by(nombre='grado_escolar').first()
        campo_colegio = CampoDemografico.query.filter_by(nombre='nombre_colegio').first()
        
        if not campo_grado:
            return []
            
        dd_grado = aliased(DatoDemografico)
        dd_colegio = aliased(DatoDemografico)
        
        query = db.session.query(
            dd_grado.valor.label('grado'),
            dd_colegio.valor.label('institucion'),
            func.count(Aplicacion.id).label('total_aplicaciones'),
            func.count(case((Aplicacion.estado == 'completada', 1))).label('completadas'),
        ).select_from(Aplicacion).join(
            Usuario, Aplicacion.usuario_id == Usuario.id
        ).join(
            dd_grado, (dd_grado.usuario_id == Usuario.id) & (dd_grado.campo_id == campo_grado.id)
        )
        
        if campo_colegio:
            query = query.outerjoin(
                dd_colegio, (dd_colegio.usuario_id == Usuario.id) & (dd_colegio.campo_id == campo_colegio.id)
            )
            
        if configuracion_id:
            query = query.filter(Aplicacion.configuracion_id == configuracion_id)
            
        resultados = query.group_by(dd_grado.valor, dd_colegio.valor if campo_colegio else Usuario.id).all()
        
        def _normalizar_grado(valor):
            if not valor:
                return 'Desconocido'
            txt = str(valor).strip().lower()
            if txt.startswith('9') or 'nov' in txt:
                return '9°'
            if txt.startswith('10') or 'dec' in txt or 'diec' in txt:
                return '10°'
            if txt.startswith('11') or 'once' in txt:
                return '11°'
            return valor

        agrupado = {}
        for r in resultados:
            grado_norm = _normalizar_grado(r.grado)
            inst_name = r.institucion if r.institucion else 'Sin especificar'
            key = (grado_norm, inst_name)
            if key not in agrupado:
                agrupado[key] = {
                    'grado': grado_norm,
                    'institucion': inst_name,
                    'total_aplicaciones': 0,
                    'completadas': 0,
                }
            agrupado[key]['total_aplicaciones'] += r.total_aplicaciones
            agrupado[key]['completadas'] += r.completadas

        return [
            {
                'grado': val['grado'],
                'institucion': val['institucion'],
                'total_aplicaciones': val['total_aplicaciones'],
                'completadas': val['completadas'],
                'tasa_completacion': round(val['completadas'] / val['total_aplicaciones'] * 100, 2) if val['total_aplicaciones'] > 0 else 0,
            }
            for val in agrupado.values()
        ]


    @staticmethod
    def estadisticas_por_institucion(configuracion_id: int = None) -> list:
        """Estadísticas agregadas por institución (usando campo demográfico 'nombre_colegio')."""
        # campo_id=13 es "Nombre del Colegio" en datos_demograficos
        campo = CampoDemografico.query.filter_by(nombre='nombre_colegio').first()
        if not campo:
            return []

        query = db.session.query(
            DatoDemografico.valor.label('institucion'),
            func.count(Aplicacion.id).label('total'),
            func.count(case((Aplicacion.estado == 'completada', 1))).label('completadas'),
        ).select_from(DatoDemografico).join(
            Usuario, Usuario.id == DatoDemografico.usuario_id
        ).join(
            Aplicacion, Aplicacion.usuario_id == Usuario.id
        ).filter(
            DatoDemografico.campo_id == campo.id
        )

        if configuracion_id:
            query = query.filter(Aplicacion.configuracion_id == configuracion_id)

        resultados = query.group_by(DatoDemografico.valor).order_by(func.count(Aplicacion.id).desc()).all()

        return [
            {
                'institucion': r.institucion,
                'total': r.total,
                'completadas': r.completadas,
                'tasa_completacion': round(r.completadas / r.total * 100, 2) if r.total > 0 else 0,
            }
            for r in resultados
        ]

    @staticmethod
    def promedios_dimensiones(configuracion_id: int = None) -> list:
        """Promedios de puntajes por dimensión."""
        query = db.session.query(
            Dimension.nombre.label('dimension'),
            func.avg(ResultadoDimension.puntaje_normalizado).label('promedio'),
            func.min(ResultadoDimension.puntaje_normalizado).label('minimo'),
            func.max(ResultadoDimension.puntaje_normalizado).label('maximo'),
            func.count(ResultadoDimension.id).label('total'),
        ).join(Dimension)

        if configuracion_id:
            query = query.join(Aplicacion).filter(
                Aplicacion.configuracion_id == configuracion_id
            )

        resultados = query.group_by(Dimension.nombre).all()

        return [
            {
                'dimension': r.dimension,
                'promedio': round(float(r.promedio), 2) if r.promedio else 0,
                'minimo': round(float(r.minimo), 2) if r.minimo else 0,
                'maximo': round(float(r.maximo), 2) if r.maximo else 0,
                'total_evaluaciones': r.total,
            }
            for r in resultados
        ]

    @staticmethod
    def estadisticas_por_tipo_colegio() -> list:
        """Estadísticas comparativas entre colegios públicos y privados."""
        campo_tipo = CampoDemografico.query.filter_by(nombre='tipo_colegio', activo=True).first()
        if not campo_tipo:
            return []

        query = db.session.query(
            DatoDemografico.valor.label('tipo_colegio'),
            func.count(func.distinct(Usuario.id)).label('estudiantes'),
            func.count(func.distinct(Aplicacion.id)).label('total_aplicaciones'),
            func.count(func.distinct(case((Aplicacion.estado == 'completada', Aplicacion.id)))).label('completadas'),
        ).select_from(DatoDemografico).join(
            Usuario, DatoDemografico.usuario_id == Usuario.id
        ).join(
            Aplicacion, Aplicacion.usuario_id == Usuario.id
        ).filter(
            DatoDemografico.campo_id == campo_tipo.id
        ).group_by(DatoDemografico.valor)

        resultados = query.all()

        return [
            {
                'tipo': r.tipo_colegio,
                'estudiantes': r.estudiantes,
                'aplicaciones': r.total_aplicaciones,
                'completadas': r.completadas,
                'tasa_completacion': round(r.completadas / r.total_aplicaciones * 100, 2) if r.total_aplicaciones > 0 else 0,
            }
            for r in resultados
        ]

    @staticmethod
    def distribucion_perfiles_por_tipo_colegio() -> list:
        """Distribución de perfiles Holland por tipo de colegio (público/privado)."""
        campo_tipo = CampoDemografico.query.filter_by(nombre='tipo_colegio', activo=True).first()
        if not campo_tipo:
            return []

        query = db.session.query(
            DatoDemografico.valor.label('tipo_colegio'),
            PerfilVocacional.perfil_principal,
            func.count(PerfilVocacional.id).label('cantidad'),
        ).select_from(DatoDemografico).join(
            Usuario, DatoDemografico.usuario_id == Usuario.id
        ).join(
            Aplicacion, Aplicacion.usuario_id == Usuario.id
        ).join(
            PerfilVocacional, PerfilVocacional.aplicacion_id == Aplicacion.id
        ).filter(
            DatoDemografico.campo_id == campo_tipo.id
        ).group_by(DatoDemografico.valor, PerfilVocacional.perfil_principal)

        resultados = query.all()

        # Agrupar por tipo de colegio
        agrupado = {}
        for r in resultados:
            if r.tipo_colegio not in agrupado:
                agrupado[r.tipo_colegio] = {'tipo_colegio': r.tipo_colegio, 'perfiles': [], 'total': 0}
            agrupado[r.tipo_colegio]['perfiles'].append({
                'perfil': r.perfil_principal,
                'cantidad': r.cantidad,
            })
            agrupado[r.tipo_colegio]['total'] += r.cantidad

        # Calcular porcentajes
        for tipo_data in agrupado.values():
            for perfil in tipo_data['perfiles']:
                perfil['porcentaje'] = round(perfil['cantidad'] / tipo_data['total'] * 100, 2) if tipo_data['total'] > 0 else 0

        return list(agrupado.values())

    @staticmethod
    def distribucion_por_areas_interes() -> list:
        """Distribución general por áreas de interés Holland."""
        query = db.session.query(
            PerfilVocacional.perfil_principal.label('area'),
            func.count(PerfilVocacional.id).label('cantidad'),
        ).group_by(PerfilVocacional.perfil_principal).order_by(func.count(PerfilVocacional.id).desc())

        resultados = query.all()
        total = sum(r.cantidad for r in resultados)

        return [
            {
                'area': r.area,
                'cantidad': r.cantidad,
                'porcentaje': round(r.cantidad / total * 100, 2) if total > 0 else 0,
            }
            for r in resultados
        ]

    @staticmethod
    def resumen_general() -> dict:
        """Resumen general del sistema (3 queries en lugar de 6)."""
        # Query 1: conteos de aplicaciones con CASE
        app_row = db.session.query(
            func.count(Aplicacion.id).label('total'),
            func.count(case((Aplicacion.estado == 'completada', 1))).label('completadas'),
        ).first()
        total_apps = app_row.total      if app_row else 0
        completadas = app_row.completadas if app_row else 0

        # Query 2: conteos de usuarios con CASE
        from ..models.usuario import Rol
        user_row = db.session.query(
            func.count(Usuario.id).label('total_activos'),
            func.count(case((Rol.nombre == 'estudiante', Usuario.id))).label('total_estudiantes'),
        ).join(Rol, Usuario.rol_id == Rol.id).filter(Usuario.activo == True).first()

        # Query 3: perfiles generados + configuraciones activas
        perfiles   = PerfilVocacional.query.count()
        configs    = ConfiguracionAplicacion.query.filter_by(activa=True).count()

        return {
            'total_usuarios': user_row.total_activos      if user_row else 0,
            'total_estudiantes': user_row.total_estudiantes if user_row else 0,
            'total_aplicaciones': total_apps,
            'aplicaciones_completadas': completadas,
            'perfiles_generados': perfiles,
            'configuraciones_activas': configs,
            'tasa_participacion': round(completadas / total_apps * 100, 1) if total_apps else 0,
        }

    @staticmethod
    def participacion_por_instrumento() -> list:
        """Participación y porcentajes por instrumento/configuración.

        Incluye todas las configuraciones activas y calcula sus estadísticas
        e históricos individualmente para evitar duplicidad y garantizar coherencia total.
        """
        # 1. Obtener todas las configuraciones activas
        configs_activas = (
            ConfiguracionAplicacion.query
            .filter_by(activa=True)
            .order_by(ConfiguracionAplicacion.obligatoria.desc(), ConfiguracionAplicacion.fecha_inicio.asc())
            .all()
        )

        if not configs_activas:
            return []

        # 2. Obtener los instrumentos relacionados
        inst_ids = list({c.instrumento_id for c in configs_activas})
        instrumentos = Instrumento.query.filter(Instrumento.id.in_(inst_ids)).all()
        inst_map = {i.id: i for i in instrumentos}

        # 3. Obtener dimensiones y escalas relacionados para optimizar en batch
        dims_all = (
            Dimension.query
            .filter(Dimension.instrumento_id.in_(inst_ids))
            .order_by(Dimension.orden)
            .all()
        )
        dims_by_inst: dict = {}
        for d in dims_all:
            dims_by_inst.setdefault(d.instrumento_id, []).append(d)

        dim_ids = [d.id for d in dims_all]
        scales_all = (
            Escala.query
            .filter(Escala.dimension_id.in_(dim_ids))
            .order_by(Escala.orden)
            .all()
        ) if dim_ids else []
        scales_by_dim: dict = {}
        for s in scales_all:
            scales_by_dim.setdefault(s.dimension_id, []).append(s)

        resultado = []
        for config in configs_activas:
            inst = inst_map.get(config.instrumento_id)
            if not inst:
                continue

            # Query counts specifically for this configuration ID
            row = db.session.query(
                func.count(Aplicacion.id).label('total'),
                func.count(case((Aplicacion.estado == 'completada', 1))).label('completadas'),
                func.count(case((Aplicacion.estado == 'en_progreso', 1))).label('en_progreso'),
            ).filter(Aplicacion.configuracion_id == config.id).first()

            total       = row.total       if row else 0
            completadas = row.completadas if row else 0
            en_progreso = row.en_progreso if row else 0

            # Query dimension averages specifically for this configuration ID
            avg_rows = db.session.query(
                ResultadoDimension.dimension_id,
                func.avg(ResultadoDimension.puntaje_normalizado).label('promedio'),
            ).join(Aplicacion).filter(
                Aplicacion.configuracion_id == config.id
            ).group_by(ResultadoDimension.dimension_id).all()

            config_avgs = {
                r.dimension_id: round(float(r.promedio), 1) if r.promedio else 0
                for r in avg_rows
            }

            puntajes_escala = []
            for dim in dims_by_inst.get(inst.id, []):
                dim_avg = config_avgs.get(dim.id, 0)
                for esc in scales_by_dim.get(dim.id, []):
                    puntajes_escala.append({
                        'escala': esc.nombre,
                        'dimension': dim.nombre,
                        'promedio': dim_avg,
                    })

            resultado.append({
                'instrumento_id': inst.id,
                'instrumento_nombre': inst.nombre,
                'config_id': config.id,
                'config_nombre': config.nombre,
                'activa': config.activa,
                'obligatoria': config.obligatoria,
                'seguimiento': not config.obligatoria,
                'total': total,
                'completadas': completadas,
                'en_progreso': en_progreso,
                'tasa_completacion': round(completadas / total * 100, 1) if total > 0 else 0,
                'puntajes_escala': puntajes_escala,
            })

        return resultado


    @staticmethod
    def distribucion_perfiles_por_instrumento() -> list:
        """Distribución de perfiles vocacionales desglosada por instrumento."""
        instrumentos = Instrumento.query.filter_by(activo=True).all()
        resultado = []

        for inst in instrumentos:
            config_ids = [
                c.id for c in ConfiguracionAplicacion.query.filter_by(instrumento_id=inst.id).all()
            ]
            if not config_ids:
                continue

            rows = db.session.query(
                PerfilVocacional.perfil_principal,
                func.count(PerfilVocacional.id).label('cantidad'),
            ).join(Aplicacion).filter(
                Aplicacion.configuracion_id.in_(config_ids)
            ).group_by(PerfilVocacional.perfil_principal).all()

            total = sum(r.cantidad for r in rows)
            resultado.append({
                'instrumento_id': inst.id,
                'instrumento_nombre': inst.nombre,
                'total_perfiles': total,
                'perfiles': [
                    {
                        'perfil': r.perfil_principal,
                        'cantidad': r.cantidad,
                        'porcentaje': round(r.cantidad / total * 100, 1) if total > 0 else 0,
                    }
                    for r in rows
                ],
            })

        return resultado

    # ─── Evolución, Mutaciones y Predicción ───────────────────────────────── #

    @staticmethod
    def evolucion_estudiante(usuario_id: int, hasta_aplicacion_id: int = None) -> dict:
        """Historial de perfiles por aplicación para mostrar la evolución vocacional."""
        # Incluir todas las aplicaciones completadas para mostrar la evolución completa (tanto base como seguimiento).
        query = (
            Aplicacion.query
            .join(ConfiguracionAplicacion, Aplicacion.configuracion_id == ConfiguracionAplicacion.id)
            .filter(
                Aplicacion.usuario_id == usuario_id,
                Aplicacion.estado == 'completada',
            )
        )

        if hasta_aplicacion_id:
            limite_ap = Aplicacion.query.get(hasta_aplicacion_id)
            if limite_ap and limite_ap.fecha_fin:
                query = query.filter(Aplicacion.fecha_fin <= limite_ap.fecha_fin)
            else:
                query = query.filter(Aplicacion.id <= hasta_aplicacion_id)

        aplicaciones = query.order_by(Aplicacion.fecha_fin).all()

        historial = []
        for ap in aplicaciones:
            perfil = PerfilVocacional.query.filter_by(aplicacion_id=ap.id).first()
            if not perfil:
                continue

            puntajes = {}
            if perfil.datos_json and 'puntajes_por_area' in perfil.datos_json:
                for area, datos in perfil.datos_json['puntajes_por_area'].items():
                    raw = datos.get('normalizado', datos.get('total', 0))
                    # Normalizar siempre a rango 0-100 para la gráfica:
                    # datos del servicio psicométrico vienen en 0-100 (usar directo);
                    # datos antiguos (seed manual) vienen en 0-1 (multiplicar × 100).
                    puntajes[area] = round(raw if raw > 1 else raw * 100, 1)

            historial.append({
                'aplicacion_id': ap.id,
                'fecha': ap.fecha_fin.strftime('%Y-%m-%d') if ap.fecha_fin else None,
                'perfil_principal': perfil.perfil_principal,
                'perfil_secundario': perfil.perfil_secundario,
                'codigo_riasec': (perfil.datos_json or {}).get('codigo_riasec', ''),
                'puntajes': puntajes,
            })

        return {'usuario_id': usuario_id, 'historial': historial}

    @staticmethod
    def mutaciones_vocacionales(usuario_id: int, hasta_aplicacion_id: int = None) -> list:
        """Detecta cambios de perfil principal entre aplicaciones (mutaciones vocacionales)."""
        historial = EstadisticaService.evolucion_estudiante(usuario_id, hasta_aplicacion_id=hasta_aplicacion_id)['historial']
        mutaciones = []

        for i in range(1, len(historial)):
            anterior = historial[i - 1]
            actual = historial[i]
            if anterior['perfil_principal'] != actual['perfil_principal']:
                mutaciones.append({
                    'desde': anterior['perfil_principal'],
                    'hacia': actual['perfil_principal'],
                    'fecha_anterior': anterior['fecha'],
                    'fecha_actual': actual['fecha'],
                    'aplicacion_anterior': anterior['aplicacion_id'],
                    'aplicacion_actual': actual['aplicacion_id'],
                })

        return mutaciones

    @staticmethod
    def prediccion_vocacional(usuario_id: int, hasta_aplicacion_id: int = None) -> dict:
        """Predice la tendencia vocacional basada en el historial de puntajes."""
        historial = EstadisticaService.evolucion_estudiante(usuario_id, hasta_aplicacion_id=hasta_aplicacion_id)['historial']

        if len(historial) < 2:
            return {
                'tiene_prediccion': False,
                'mensaje': 'Se necesitan al menos 2 aplicaciones para generar una predicción.',
                'tendencias': [],
            }

        # Calcular tendencia lineal por área (pendiente simple)
        tendencias = []
        for area in RIASEC_AREAS:
            valores = [h['puntajes'].get(area, 0) for h in historial]
            n = len(valores)
            if n < 2:
                continue

            # Regresión lineal simple
            x_vals = list(range(n))
            x_mean = sum(x_vals) / n
            y_mean = sum(valores) / n
            num = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, valores))
            den = sum((x - x_mean) ** 2 for x in x_vals)
            pendiente = num / den if den != 0 else 0

            ultimo = valores[-1]
            predicho = round(min(100, max(0, ultimo + pendiente)), 1)

            tendencias.append({
                'area': area,
                'puntaje_actual': round(ultimo, 1),
                'prediccion_proxima': predicho,
                'tendencia': 'creciente' if pendiente > 1 else ('decreciente' if pendiente < -1 else 'estable'),
                'cambio_esperado': round(pendiente, 2),
            })

        tendencias.sort(key=lambda x: x['prediccion_proxima'], reverse=True)
        perfil_predicho = tendencias[0]['area'] if tendencias else None

        return {
            'tiene_prediccion': True,
            'perfil_predicho': perfil_predicho,
            'tendencias': tendencias,
            'basado_en': len(historial),
        }

    # ─── Segmentación por Género ───────────────────────────────────────────── #

    @staticmethod
    def segmentacion_genero() -> list:
        """Distribución de perfiles vocacionales segmentada por género."""
        campo_genero = CampoDemografico.query.filter_by(nombre='genero', activo=True).first()
        if not campo_genero:
            return []

        rows = db.session.query(
            DatoDemografico.valor.label('genero'),
            PerfilVocacional.perfil_principal,
            func.count(PerfilVocacional.id).label('cantidad'),
        ).select_from(DatoDemografico).join(
            Usuario, DatoDemografico.usuario_id == Usuario.id
        ).join(
            Aplicacion, Aplicacion.usuario_id == Usuario.id
        ).join(
            PerfilVocacional, PerfilVocacional.aplicacion_id == Aplicacion.id
        ).filter(
            DatoDemografico.campo_id == campo_genero.id,
            Aplicacion.estado == 'completada',
        ).group_by(DatoDemografico.valor, PerfilVocacional.perfil_principal).all()

        agrupado = {}
        for r in rows:
            genero = r.genero or 'No especificado'
            if genero not in agrupado:
                agrupado[genero] = {'genero': genero, 'perfiles': {}, 'total': 0}
            agrupado[genero]['perfiles'][r.perfil_principal] = r.cantidad
            agrupado[genero]['total'] += r.cantidad

        resultado = []
        for genero, datos in agrupado.items():
            perfiles_lista = []
            for perfil, cant in datos['perfiles'].items():
                perfiles_lista.append({
                    'perfil': perfil,
                    'cantidad': cant,
                    'porcentaje': round(cant / datos['total'] * 100, 1) if datos['total'] > 0 else 0,
                })
            resultado.append({
                'genero': genero,
                'total': datos['total'],
                'perfiles': sorted(perfiles_lista, key=lambda x: x['cantidad'], reverse=True),
            })

        return sorted(resultado, key=lambda x: x['total'], reverse=True)

    @staticmethod
    def conteo_por_genero() -> list:
        """Conteo total de estudiantes por género."""
        campo_genero = CampoDemografico.query.filter_by(nombre='genero', activo=True).first()
        if not campo_genero:
            return []

        rows = db.session.query(
            DatoDemografico.valor.label('genero'),
            func.count(func.distinct(DatoDemografico.usuario_id)).label('cantidad'),
        ).filter(
            DatoDemografico.campo_id == campo_genero.id
        ).group_by(DatoDemografico.valor).all()

        total = sum(r.cantidad for r in rows)
        return [
            {
                'genero': r.genero or 'No especificado',
                'cantidad': r.cantidad,
                'porcentaje': round(r.cantidad / total * 100, 1) if total > 0 else 0,
            }
            for r in rows
        ]

    # ─── Segmentación por Edad ─────────────────────────────────────────────── #

    @staticmethod
    def segmentacion_edad() -> list:
        """Distribución de perfiles vocacionales segmentada por rango de edad."""
        campo_edad = CampoDemografico.query.filter_by(nombre='edad', activo=True).first()
        if not campo_edad:
            return []

        rows = db.session.query(
            DatoDemografico.valor.label('edad_raw'),
            PerfilVocacional.perfil_principal,
            func.count(PerfilVocacional.id).label('cantidad'),
        ).select_from(DatoDemografico).join(
            Usuario, DatoDemografico.usuario_id == Usuario.id
        ).join(
            Aplicacion, Aplicacion.usuario_id == Usuario.id
        ).join(
            PerfilVocacional, PerfilVocacional.aplicacion_id == Aplicacion.id
        ).filter(
            DatoDemografico.campo_id == campo_edad.id,
            Aplicacion.estado == 'completada',
        ).group_by(DatoDemografico.valor, PerfilVocacional.perfil_principal).all()

        def clasificar_edad(edad_str):
            try:
                edad = int(edad_str)
            except (ValueError, TypeError):
                return 'No especificado'
            if edad <= 14:
                return '≤14 años'
            elif edad <= 15:
                return '15 años'
            elif edad <= 16:
                return '16 años'
            elif edad <= 17:
                return '17 años'
            elif edad <= 18:
                return '18 años'
            else:
                return '19+ años'

        agrupado = {}
        for r in rows:
            rango = clasificar_edad(r.edad_raw)
            if rango not in agrupado:
                agrupado[rango] = {'rango_edad': rango, 'perfiles': {}, 'total': 0}
            agrupado[rango]['perfiles'][r.perfil_principal] = (
                agrupado[rango]['perfiles'].get(r.perfil_principal, 0) + r.cantidad
            )
            agrupado[rango]['total'] += r.cantidad

        orden_rangos = ['≤14 años', '15 años', '16 años', '17 años', '18 años', '19+ años', 'No especificado']
        resultado = []
        for rango in orden_rangos:
            if rango not in agrupado:
                continue
            datos = agrupado[rango]
            perfiles_lista = [
                {
                    'perfil': perfil,
                    'cantidad': cant,
                    'porcentaje': round(cant / datos['total'] * 100, 1) if datos['total'] > 0 else 0,
                }
                for perfil, cant in datos['perfiles'].items()
            ]
            resultado.append({
                'rango_edad': rango,
                'total': datos['total'],
                'perfiles': sorted(perfiles_lista, key=lambda x: x['cantidad'], reverse=True),
            })

        return resultado

    @staticmethod
    def conteo_por_edad() -> list:
        """Conteo de estudiantes por rango de edad."""
        campo_edad = CampoDemografico.query.filter_by(nombre='edad', activo=True).first()
        if not campo_edad:
            return []

        rows = db.session.query(
            DatoDemografico.valor.label('edad_raw'),
            func.count(func.distinct(DatoDemografico.usuario_id)).label('cantidad'),
        ).filter(
            DatoDemografico.campo_id == campo_edad.id
        ).group_by(DatoDemografico.valor).all()

        def clasificar(val):
            try:
                e = int(val)
            except (ValueError, TypeError):
                return 'No especificado'
            if e <= 14:
                return '≤14 años'
            elif e <= 15:
                return '15 años'
            elif e <= 16:
                return '16 años'
            elif e <= 17:
                return '17 años'
            elif e <= 18:
                return '18 años'
            else:
                return '19+ años'

        agrupado = {}
        for r in rows:
            rango = clasificar(r.edad_raw)
            agrupado[rango] = agrupado.get(rango, 0) + r.cantidad

        orden_rangos = ['≤14 años', '15 años', '16 años', '17 años', '18 años', '19+ años', 'No especificado']
        total = sum(agrupado.values())
        return [
            {
                'rango_edad': rango,
                'cantidad': agrupado[rango],
                'porcentaje': round(agrupado[rango] / total * 100, 1) if total > 0 else 0,
            }
            for rango in orden_rangos if rango in agrupado
        ]

    # ─── Resumen de evolución para listado admin ───────────────────────────── #

    @staticmethod
    def resumen_evolucion_estudiantes(buscar: str = '', page: int = 1, per_page: int = 20) -> dict:
        """Lista todos los estudiantes con conteo de pruebas y último perfil."""
        from ..models.usuario import Rol

        def _normalizar_grado(valor: str) -> str:
            if not valor:
                return None
            txt = str(valor).strip().lower()
            if txt.startswith('9'):
                return '9°'
            if txt.startswith('10'):
                return '10°'
            if txt.startswith('11'):
                return '11°'
            return None

        # Subquery: total de pruebas completadas y última app por estudiante
        sub = (
            db.session.query(
                Aplicacion.usuario_id,
                func.count(Aplicacion.id).label('total_pruebas'),
                func.max(Aplicacion.id).label('ultima_app_id'),
            )
            .filter(Aplicacion.estado == 'completada')
            .group_by(Aplicacion.usuario_id)
            .subquery()
        )

        query = (
            db.session.query(
                Usuario,
                func.coalesce(sub.c.total_pruebas, 0).label('total_pruebas'),
                sub.c.ultima_app_id,
            )
            .join(Rol, Usuario.rol_id == Rol.id)
            .filter(Rol.nombre == 'estudiante', Usuario.activo == True)
            .outerjoin(sub, Usuario.id == sub.c.usuario_id)
        )

        if buscar:
            termino = f'%{buscar}%'
            query = query.filter(
                (Usuario.nombres.ilike(termino)) |
                (Usuario.apellidos.ilike(termino)) |
                (Usuario.email.ilike(termino))
            )

        total = query.count()
        paginas = max(1, (total + per_page - 1) // per_page)
        rows = (
            query
            .order_by(Usuario.apellidos, Usuario.nombres)
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        usuario_ids = [r.Usuario.id for r in rows]
        grados_demo_map: dict = {}
        if usuario_ids:
            campo_grado = CampoDemografico.query.filter_by(nombre='grado_escolar', activo=True).first()
            if campo_grado:
                datos_grado = (
                    DatoDemografico.query
                    .filter(
                        DatoDemografico.campo_id == campo_grado.id,
                        DatoDemografico.usuario_id.in_(usuario_ids),
                    )
                    .all()
                )
                grados_demo_map = {
                    d.usuario_id: _normalizar_grado(d.valor)
                    for d in datos_grado
                    if d.valor
                }

        # Cargar perfiles y fechas en batch (evita N+1)
        ultima_app_ids = [r.ultima_app_id for r in rows if r.ultima_app_id]
        perfiles_map: dict = {}
        fechas_map: dict = {}
        if ultima_app_ids:
            perfiles = PerfilVocacional.query.filter(
                PerfilVocacional.aplicacion_id.in_(ultima_app_ids)
            ).all()
            perfiles_map = {p.aplicacion_id: p.perfil_principal for p in perfiles}
            apps = Aplicacion.query.filter(Aplicacion.id.in_(ultima_app_ids)).all()
            fechas_map = {a.id: a.fecha_fin for a in apps}

        estudiantes = []
        for usuario, total_pruebas, ultima_app_id in rows:
            ultima_fecha_dt = fechas_map.get(ultima_app_id) if ultima_app_id else None
            grado = _normalizar_grado(usuario.grado.nombre if usuario.grado else None)
            if not grado:
                grado = grados_demo_map.get(usuario.id)
            if not grado:
                grado = '11°'
            estudiantes.append({
                'id': usuario.id,
                'nombre_completo': usuario.nombre_completo,
                'email': usuario.email,
                'grado_nombre': grado,
                'total_pruebas': int(total_pruebas or 0),
                'ultima_fecha': ultima_fecha_dt.strftime('%Y-%m-%d') if ultima_fecha_dt else None,
                'ultimo_perfil': perfiles_map.get(ultima_app_id) if ultima_app_id else None,
            })

        return {
            'estudiantes': estudiantes,
            'total': total,
            'paginas': paginas,
            'pagina_actual': page,
        }

