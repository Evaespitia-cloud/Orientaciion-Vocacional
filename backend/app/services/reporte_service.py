"""Servicio de generación de reportes PDF."""

import os
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF
from ..extensions import db
from ..models.resultado import PerfilVocacional, Reporte


class ReporteService:
    """Servicio para generación de reportes PDF."""

    REPORTES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'reportes')

    RIASEC_COLORS_RL = [
        colors.HexColor('#4f46e5'),
        colors.HexColor('#0d9488'),
        colors.HexColor('#f59e0b'),
        colors.HexColor('#ef4444'),
        colors.HexColor('#8b5cf6'),
        colors.HexColor('#06b6d4'),
    ]

    @staticmethod
    def _grafico_barras_holland(puntajes_por_area: dict, width: float = 450, height: float = 200) -> Drawing:
        """Crea un gráfico de barras horizontal con los puntajes Holland RIASEC."""
        areas = list(puntajes_por_area.keys())
        valores = [puntajes_por_area[a].get('normalizado', 0) for a in areas]

        drawing = Drawing(width, height)

        # Fondo
        drawing.add(Rect(0, 0, width, height, fillColor=colors.HexColor('#f8fafc'), strokeColor=None))

        bar_height = min(20, (height - 30) / max(len(areas), 1))
        y_step = (height - 30) / max(len(areas), 1)
        label_width = 100
        bar_area_width = width - label_width - 60

        for i, (area, valor) in enumerate(zip(areas, valores)):
            y = height - 20 - (i + 0.5) * y_step
            bar_w = (valor / 100) * bar_area_width

            col = ReporteService.RIASEC_COLORS_RL[i % len(ReporteService.RIASEC_COLORS_RL)]

            # Barra de fondo gris
            drawing.add(Rect(label_width, y - bar_height / 2, bar_area_width, bar_height,
                            fillColor=colors.HexColor('#e2e8f0'), strokeColor=None))
            # Barra de valor
            if bar_w > 0:
                drawing.add(Rect(label_width, y - bar_height / 2, bar_w, bar_height,
                                fillColor=col, strokeColor=None))

            # Etiqueta área
            drawing.add(String(label_width - 4, y - 5, area,
                               fontName='Helvetica-Bold', fontSize=8,
                               fillColor=colors.HexColor('#2d3748'),
                               textAnchor='end'))

            # Porcentaje
            drawing.add(String(label_width + bar_area_width + 4, y - 5, f'{valor:.0f}%',
                               fontName='Helvetica-Bold', fontSize=8,
                               fillColor=col, textAnchor='start'))

        # Líneas de referencia (25%, 50%, 75%, 100%)
        for pct in [25, 50, 75, 100]:
            x = label_width + (pct / 100) * bar_area_width
            drawing.add(Line(x, 0, x, height - 20,
                            strokeColor=colors.HexColor('#cbd5e0'), strokeWidth=0.5,
                            strokeDashArray=[3, 3]))
            drawing.add(String(x, 2, f'{pct}%',
                               fontName='Helvetica', fontSize=6,
                               fillColor=colors.HexColor('#94a3b8'),
                               textAnchor='middle'))

        return drawing

    @staticmethod
    def _grafico_pastel_perfiles(perfil_principal: str, puntajes_por_area: dict,
                                  width: float = 220, height: float = 180) -> Drawing:
        """Gráfico tipo pastel con distribución de áreas."""
        areas = list(puntajes_por_area.keys())
        valores = [max(0.01, puntajes_por_area[a].get('normalizado', 0)) for a in areas]

        drawing = Drawing(width, height)
        pie = Pie()
        pie.x = (width - 140) // 2
        pie.y = (height - 140) // 2
        pie.width = 140
        pie.height = 140
        pie.data = valores
        pie.labels = [f'{a[:3]}' for a in areas]
        pie.sideLabels = False
        pie.simpleLabels = True
        pie.startAngle = 90

        for i in range(len(areas)):
            col = ReporteService.RIASEC_COLORS_RL[i % len(ReporteService.RIASEC_COLORS_RL)]
            pie.slices[i].fillColor = col
            pie.slices[i].strokeColor = colors.white
            pie.slices[i].strokeWidth = 1.5
            # Resaltar perfil principal
            if areas[i] == perfil_principal:
                pie.slices[i].popout = 8

        drawing.add(pie)
        return drawing

    @staticmethod
    def generar_reporte_individual(perfil_id: int, generado_por: int = None) -> Reporte:
        """Genera un reporte PDF individual para un perfil vocacional."""
        perfil = PerfilVocacional.query.get_or_404(perfil_id)
        aplicacion = perfil.aplicacion
        usuario = aplicacion.usuario

        # Crear directorio de reportes si no existe
        os.makedirs(ReporteService.REPORTES_DIR, exist_ok=True)

        # Nombre del archivo
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f'reporte_{usuario.documento or usuario.id}_{timestamp}.pdf'
        filepath = os.path.join(ReporteService.REPORTES_DIR, filename)

        # Crear el PDF
        doc = SimpleDocTemplate(filepath, pagesize=letter,
                                topMargin=0.75*inch, bottomMargin=0.75*inch)
        styles = getSampleStyleSheet()

        # Estilos personalizados
        titulo_style = ParagraphStyle(
            'TituloReporte', parent=styles['Title'],
            fontSize=20, textColor=colors.HexColor('#1a365d'),
            spaceAfter=20,
        )
        subtitulo_style = ParagraphStyle(
            'Subtitulo', parent=styles['Heading2'],
            fontSize=14, textColor=colors.HexColor('#2d3748'),
            spaceBefore=15, spaceAfter=10,
        )
        normal_style = ParagraphStyle(
            'NormalCustom', parent=styles['Normal'],
            fontSize=11, leading=16,
        )

        elements = []

        # Encabezado
        elements.append(Paragraph('REPORTE DE ORIENTACIÓN VOCACIONAL', titulo_style))
        elements.append(Paragraph('Plataforma de Orientación Vocacional para Bachilleres', styles['Normal']))
        elements.append(Spacer(1, 20))

        # Datos del estudiante
        elements.append(Paragraph('Datos del Estudiante', subtitulo_style))
        datos_estudiante = [
            ['Nombre:', f'{usuario.nombres} {usuario.apellidos}'],
            ['Documento:', f'{usuario.tipo_documento} {usuario.documento or "N/A"}'],
            ['Institución:', usuario.grado.nombre if usuario.grado else 'No especificada'],
            ['Grado:', str(usuario.semestre) + '°' if usuario.semestre else 'N/A'],
            ['Fecha de aplicación:', aplicacion.fecha_inicio.strftime('%d/%m/%Y %H:%M') if aplicacion.fecha_inicio else 'N/A'],
        ]
        tabla_datos = Table(datos_estudiante, colWidths=[2*inch, 4*inch])
        tabla_datos.setStyle(TableStyle([
            ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 10),
            ('FONT', (1, 0), (1, -1), 'Helvetica', 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#4a5568')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(tabla_datos)
        elements.append(Spacer(1, 20))

        # Perfil Vocacional Principal
        elements.append(Paragraph('Perfil Vocacional', subtitulo_style))
        elements.append(Paragraph(
            f'<b>Perfil Principal:</b> {perfil.perfil_principal}', normal_style
        ))
        if perfil.perfil_secundario:
            elements.append(Paragraph(
                f'<b>Perfil Secundario:</b> {perfil.perfil_secundario}', normal_style
            ))
        elements.append(Spacer(1, 10))

        if perfil.descripcion:
            elements.append(Paragraph(perfil.descripcion, normal_style))
        elements.append(Spacer(1, 15))

        # ── Gráfico de Perfil Holland RIASEC ──────────────────────────────
        if perfil.datos_json and 'puntajes_por_area' in perfil.datos_json:
            puntajes_por_area = perfil.datos_json['puntajes_por_area']

            elements.append(Paragraph('Perfil Holland RIASEC — Resultados por Área', subtitulo_style))

            # Gráfico de barras horizontal
            grafico_barras = ReporteService._grafico_barras_holland(puntajes_por_area, width=450, height=210)
            elements.append(grafico_barras)
            elements.append(Spacer(1, 12))

            # Tabla resumen de áreas
            tabla_areas = [['Área Holland', 'Puntaje (%)', 'Nivel', 'Perfil']]
            for area, datos in sorted(puntajes_por_area.items(), key=lambda x: x[1].get('normalizado', 0), reverse=True):
                pn = datos.get('normalizado', 0)
                if pn >= 80:
                    nivel = 'Muy Alto'
                elif pn >= 60:
                    nivel = 'Alto'
                elif pn >= 40:
                    nivel = 'Medio'
                else:
                    nivel = 'Bajo'
                es_principal = '★ Principal' if area == perfil.perfil_principal else (
                    '● Secundario' if area == perfil.perfil_secundario else ''
                )
                tabla_areas.append([area, f'{pn:.1f}%', nivel, es_principal])

            t_areas = Table(tabla_areas, colWidths=[1.8*inch, 1.2*inch, 1*inch, 1.5*inch])
            t_areas.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a365d')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 9),
                ('FONT', (0, 1), (-1, -1), 'Helvetica', 9),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f4ff')]),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('TEXTCOLOR', (3, 1), (3, -1), colors.HexColor('#4f46e5')),
                ('FONT', (3, 1), (3, -1), 'Helvetica-Bold', 8),
            ]))
            elements.append(t_areas)
            elements.append(Spacer(1, 20))

        # ── Gráfico de barras por escala (detalle) ────────────────────────
        if perfil.datos_json and 'puntajes_escala' in perfil.datos_json:
            elements.append(Paragraph('Resultados por Escala — Detalle', subtitulo_style))

            puntajes = perfil.datos_json['puntajes_escala']

            # Tabla de resultados
            tabla_resultados = [['Escala', 'Dimensión', 'Puntaje (%)', 'Nivel']]
            for nombre, datos in puntajes.items():
                pn = datos['puntaje_normalizado']
                if pn >= 80:
                    nivel = 'Muy Alto'
                elif pn >= 60:
                    nivel = 'Alto'
                elif pn >= 40:
                    nivel = 'Medio'
                else:
                    nivel = 'Bajo'
                tabla_resultados.append([nombre, datos['dimension'], f"{pn:.1f}%", nivel])

            t = Table(tabla_resultados, colWidths=[2*inch, 1.5*inch, 1*inch, 1*inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 9),
                ('FONT', (0, 1), (-1, -1), 'Helvetica', 9),
                ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')]),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 20))

        # Fortalezas
        elements.append(Paragraph('Fortalezas Identificadas', subtitulo_style))
        for linea in (perfil.fortalezas or '').split('\n'):
            if linea.strip():
                elements.append(Paragraph(linea, normal_style))
        elements.append(Spacer(1, 10))

        # Áreas de desarrollo
        elements.append(Paragraph('Áreas de Desarrollo', subtitulo_style))
        for linea in (perfil.areas_desarrollo or '').split('\n'):
            if linea.strip():
                elements.append(Paragraph(linea, normal_style))
        elements.append(Spacer(1, 10))

        # Recomendaciones
        elements.append(Paragraph('Recomendaciones', subtitulo_style))
        for linea in (perfil.recomendaciones or '').split('\n'):
            if linea.strip():
                elements.append(Paragraph(linea, normal_style))
        elements.append(Spacer(1, 20))

        # Pie de página
        elements.append(Paragraph(
            f'<i>Reporte generado automáticamente el {datetime.utcnow().strftime("%d/%m/%Y %H:%M")}. '
            'Este reporte es una herramienta de orientación y no constituye un diagnóstico definitivo. '
            'Se recomienda consultar con el orientador escolar o consejero de tu institución educativa.</i>',
            ParagraphStyle('Pie', parent=styles['Normal'], fontSize=8, textColor=colors.grey)
        ))

        # Generar PDF
        doc.build(elements)

        # Registrar reporte en BD
        reporte = Reporte(
            perfil_id=perfil_id,
            tipo='individual',
            ruta_archivo=filepath,
            formato='pdf',
            generado_por=generado_por,
        )
        db.session.add(reporte)
        db.session.commit()

        return reporte
