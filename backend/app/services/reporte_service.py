"""Servicio de generación de reportes PDF."""

import os
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak,
)

from ..extensions import db
from ..models.resultado import PerfilVocacional, Reporte
from .psicometrico_service import PsicometricoService
from .reporte_graficos import TONOS_AREA, TONO_NEUTRO, BarrasAreas, Cuadros, Luz
from .reporte_respuestas import filas_de_aplicacion, porcentajes_area

AREAS = ['Realista', 'Investigador', 'Artístico', 'Social', 'Emprendedor', 'Convencional']
RECURSOS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'recursos')
MASCOTA_DIR = os.path.join(RECURSOS_DIR, 'mascota')
LOGO_USB = os.path.join(RECURSOS_DIR, 'logo-usb.png')
MASCOTA_POR_PERFIL = {
    'Realista': 'realista', 'Investigador': 'investigador', 'Artístico': 'artistico',
    'Social': 'social', 'Emprendedor': 'emprendedor', 'Convencional': 'convencional',
}
TINTA = colors.HexColor('#1c1b22')
GRIS = colors.HexColor('#6f6b80')
GRIS_SUAVE = colors.HexColor('#8a8696')
LINEA = colors.HexColor('#ece8e1')
FONDO_FILA = colors.HexColor('#faf8f5')
NARANJA_USB = colors.HexColor('#ef7d00')
ACENTO = colors.HexColor('#a35200')
# Márgenes de 0.8 in y el relleno de 6 pt a cada lado que deja el marco de reportlab.
ANCHO_UTIL = letter[0] - 1.6 * inch - 12


def ruta_mascota(perfil_principal):
    """Zorro del perfil principal; el de por defecto si el perfil no tiene uno."""
    ruta = os.path.join(MASCOTA_DIR, MASCOTA_POR_PERFIL.get(perfil_principal, 'default') + '.png')
    return ruta if os.path.exists(ruta) else os.path.join(MASCOTA_DIR, 'default.png')


def _hex(color):
    return colors.HexColor(color)


class ReporteService:
    """Servicio para generación de reportes PDF."""

    REPORTES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'reportes')

    @staticmethod
    def _estilos():
        base = getSampleStyleSheet()['Normal']

        def estilo(nombre, **kw):
            opciones = dict(fontName='Helvetica', fontSize=9, leading=12, textColor=TINTA)
            opciones.update(kw)
            return ParagraphStyle(nombre, parent=base, **opciones)

        return {
            'marca': estilo('Marca', fontSize=8, leading=11, textColor=GRIS, alignment=TA_RIGHT),
            'eyebrow': estilo('Eyebrow', fontName='Helvetica-Bold', fontSize=7.5, leading=10, textColor=ACENTO),
            'perfil': estilo('Perfil', fontName='Helvetica-Bold', fontSize=30, leading=34, spaceBefore=2, spaceAfter=4),
            'perfil_sub': estilo('PerfilSub', fontName='Helvetica-Bold', fontSize=9.5, leading=13),
            'lema': estilo('Lema', fontSize=10, leading=14.5, spaceBefore=8),
            'dato_etq': estilo('DatoEtq', fontName='Helvetica-Bold', fontSize=6.8, leading=9, textColor=GRIS_SUAVE),
            'dato': estilo('Dato', fontSize=9.5, leading=12.5),
            'h2': estilo('H2', fontName='Helvetica-Bold', fontSize=13, leading=16),
            'ayuda': estilo('Ayuda', fontSize=7.8, leading=10.5, textColor=GRIS),
            'num': estilo('Num', fontSize=8, textColor=GRIS_SUAVE),
            'fila': estilo('Fila', fontSize=8.5, leading=10.5),
            'letra': estilo('Letra', fontName='Helvetica-Bold', alignment=TA_CENTER),
            'subtotal': estilo('Subtotal', fontSize=7.8, leading=10.5, alignment=TA_CENTER),
            'texto': estilo('Texto', fontSize=9.5, leading=13.5, spaceBefore=6),
            'pie': estilo('Pie', fontSize=7.5, leading=10, textColor=GRIS),
        }

    # ── Página 1 ──────────────────────────────────────────────────────────

    @staticmethod
    def _franja_institucional(fecha, st):
        """Logo de la USB a la izquierda y el nombre del informe a la derecha."""
        logo = Image(LOGO_USB, width=1.95 * inch, height=1.95 * inch * 234 / 771)
        texto = Paragraph(
            '<b>Informe de orientación vocacional</b><br/>'
            f'{fecha.strftime("%d/%m/%Y") if fecha else ""}', st['marca'])
        franja = Table([[logo, texto]], colWidths=[ANCHO_UTIL * 0.5, ANCHO_UTIL * 0.5])
        franja.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LINEBELOW', (0, 0), (-1, 0), 2, NARANJA_USB),
        ]))
        return franja

    @staticmethod
    def _bloque_perfil(perfil, dj, st):
        """Bloque con el color del perfil: nombre, código, primera frase y el zorro."""
        color, oscuro, claro = TONOS_AREA.get(perfil.perfil_principal, TONO_NEUTRO)
        sub = []
        if dj.get('codigo_riasec'):
            sub.append(f'Código RIASEC {escape(dj["codigo_riasec"])}')
        if perfil.perfil_secundario:
            sub.append(f'Perfil secundario: {escape(perfil.perfil_secundario)}')
        texto = [
            Paragraph('TU PERFIL VOCACIONAL', st['eyebrow']),
            Paragraph(f'<font color="{oscuro}">{escape(perfil.perfil_principal or "Sin determinar")}</font>', st['perfil']),
        ]
        if sub:
            texto.append(Paragraph(f'<font color="{oscuro}">{" · ".join(sub)}</font>', st['perfil_sub']))
        if perfil.descripcion:
            texto.append(Paragraph(escape(perfil.descripcion.split('.')[0].strip()) + '.', st['lema']))
        zorro = Image(ruta_mascota(perfil.perfil_principal), width=1.9 * inch, height=1.9 * inch,
                      kind='proportional')
        bloque = Table([[texto, zorro]], colWidths=[ANCHO_UTIL - 2.15 * inch, 2.15 * inch])
        bloque.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), _hex(claro)),
            ('ROUNDEDCORNERS', [12, 12, 12, 12]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('LEFTPADDING', (0, 0), (0, 0), 20),
            ('RIGHTPADDING', (-1, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 16),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
        ]))
        return bloque

    @staticmethod
    def _datos_estudiante(usuario, aplicacion, st):
        """Tarjeta con los datos del estudiante en dos filas de tres columnas."""
        fecha = aplicacion.fecha_fin or aplicacion.fecha_inicio
        datos = [
            ('ESTUDIANTE', f'{usuario.nombres} {usuario.apellidos}'),
            ('DOCUMENTO', f'{usuario.tipo_documento or ""} {usuario.documento or "N/A"}'.strip()),
            ('FECHA DE LA PRUEBA', fecha.strftime('%d/%m/%Y') if fecha else 'N/A'),
            ('INSTITUCIÓN', usuario.grado.nombre if usuario.grado else 'No especificada'),
            ('GRADO', f'{usuario.semestre}°' if usuario.semestre else 'N/A'),
            ('CORREO', usuario.email or ''),
        ]
        celdas = [[Paragraph(etq, st['dato_etq']), Paragraph(escape(str(val)), st['dato'])] for etq, val in datos]
        filas = [celdas[0:3], celdas[3:6]]
        tabla = Table(filas, colWidths=[ANCHO_UTIL / 3] * 3)
        tabla.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.8, LINEA),
            ('ROUNDEDCORNERS', [10, 10, 10, 10]),
            ('LINEBELOW', (0, 0), (-1, 0), 0.6, LINEA),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        return tabla

    @staticmethod
    def _resultados_por_area(dj, st):
        """Barras de los seis campos de mayor a menor, con el % de la página.
        Los empates quedan en el orden del perfil."""
        puntajes = dj.get('puntajes_por_area', {})
        orden = [a for a in (dj.get('ranking_intereses') or []) if a in AREAS]
        orden += [a for a in AREAS if a not in orden]
        filas = [(area, *porcentajes_area(puntajes.get(area))) for area in orden]
        filas.sort(key=lambda f: -f[1])
        return [
            Paragraph('Tus resultados por área', st['h2']),
            Paragraph('De mayor a menor. Porcentaje combinado de intereses y competencias, el mismo de la página de resultados.',
                      st['ayuda']),
            Spacer(1, 10),
            BarrasAreas(filas, ANCHO_UTIL),
        ]

    # ── Respuestas ────────────────────────────────────────────────────────

    @staticmethod
    def _titulo_seccion(titulo, ayuda, st):
        """Título con una barra naranja a la izquierda y la ayuda debajo."""
        tabla = Table([[None, [Paragraph(titulo, st['h2']), Paragraph(ayuda, st['ayuda'])]]],
                      colWidths=[4, ANCHO_UTIL - 4])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), NARANJA_USB),
            ('LEFTPADDING', (0, 0), (0, 0), 0),
            ('RIGHTPADDING', (0, 0), (0, 0), 0),
            ('LEFTPADDING', (1, 0), (1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        return tabla

    @staticmethod
    def _subtotales(puntajes, es_interes, st):
        """Puntos por campo en la prueba, por ejemplo 'Realista 13 de 25'."""
        clave_p, clave_m = ('interes_puntaje', 'interes_maximo') if es_interes else ('competencia_puntaje', 'competencia_maximo')
        celdas, fondos = [], []
        for area in AREAS:
            d = puntajes.get(area) or {}
            maximo = d.get(clave_m) or 0
            if not maximo:
                continue
            _, oscuro, claro = TONOS_AREA[area]
            celdas.append(Paragraph(
                f'<font color="{oscuro}"><b>{area}</b></font><br/><b>{d.get(clave_p, 0)}</b> de {maximo}',
                st['subtotal']))
            fondos.append(claro)
        if not celdas:
            return Spacer(1, 0)
        tabla = Table([celdas], colWidths=[ANCHO_UTIL / len(celdas)] * len(celdas))
        estilo = [('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
                  ('LINEAFTER', (0, 0), (-2, -1), 3, colors.white)]
        estilo += [('BACKGROUND', (i, 0), (i, 0), _hex(c)) for i, c in enumerate(fondos)]
        tabla.setStyle(TableStyle(estilo))
        return tabla

    @staticmethod
    def _seccion_respuestas(prueba, es_interes, puntajes, st):
        """Una fila por pregunta: número, enunciado, letra y su valor dibujado."""
        if es_interes:
            titulo = 'Prueba de intereses'
            ayuda = ('Luz encendida: elegiste la opción A y el punto fue para el campo de la pregunta. '
                     'Apagada: elegiste la B y el punto fue para el otro campo.')
        else:
            titulo = 'Prueba de competencias'
            ayuda = 'Cuadros sombreados: los puntos que valió tu respuesta, de 1 a 4.'

        datos = []
        for f in filas_de_aplicacion(prueba):
            dibujo = Luz(f['valor'], f['area']) if f['tipo'] == 'luz' else Cuadros(f['valor'], f['maximo'], f['area'])
            datos.append([
                Paragraph(f"{f['numero']}", st['num']),
                Paragraph(escape(f['enunciado']), st['fila']),
                Paragraph(f['letra'], st['letra']),
                dibujo,
            ])
        elementos = [ReporteService._titulo_seccion(titulo, ayuda, st), Spacer(1, 8)]
        if datos:
            tabla = Table(datos, colWidths=[0.35 * inch, ANCHO_UTIL - 2.05 * inch, 0.35 * inch, 1.35 * inch],
                          repeatRows=0)
            tabla.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, FONDO_FILA]),
                ('TOPPADDING', (0, 0), (-1, -1), 3.5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
                ('LEFTPADDING', (0, 0), (0, -1), 8),
            ]))
            elementos.append(tabla)
        elementos += [Spacer(1, 8), ReporteService._subtotales(puntajes, es_interes, st), Spacer(1, 20)]
        return elementos

    # ── Cierre ────────────────────────────────────────────────────────────

    @staticmethod
    def _cierre(perfil, dj, st):
        """Recuadro final con el perfil, su ambiente de trabajo y los programas de la USB."""
        _, oscuro, claro = TONOS_AREA.get(perfil.perfil_principal, TONO_NEUTRO)
        partes = [Paragraph('PERFIL VOCACIONAL', st['eyebrow']),
                  Paragraph(f'<font color="{oscuro}">{escape(perfil.perfil_principal or "Sin determinar")}</font>',
                            st['perfil'])]
        if perfil.descripcion:
            partes.append(Paragraph(escape(perfil.descripcion), st['texto']))
        if dj.get('ambiente_trabajo'):
            partes.append(Paragraph('<b>Ambiente de trabajo ideal:</b> ' + escape(dj['ambiente_trabajo']), st['texto']))
        nombres = [p.get('nombre') for p in (dj.get('programas_usb') or []) if p.get('nombre')]
        if nombres:
            partes.append(Paragraph('<b>Programas de la USB relacionados con tu perfil:</b> '
                                    + escape(' · '.join(nombres)), st['texto']))
        recuadro = Table([[partes]], colWidths=[ANCHO_UTIL])
        recuadro.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), _hex(claro)),
            ('ROUNDEDCORNERS', [12, 12, 12, 12]),
            ('LEFTPADDING', (0, 0), (-1, -1), 20),
            ('RIGHTPADDING', (0, 0), (-1, -1), 20),
            ('TOPPADDING', (0, 0), (-1, -1), 16),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 18),
        ]))
        return KeepTogether([recuadro, Spacer(1, 10), Paragraph(
            'Este informe es una herramienta de orientación y no un diagnóstico definitivo. '
            'Se recomienda revisarlo con el orientador de tu colegio o con Bienestar de la USB.', st['pie'])])

    @staticmethod
    def generar_reporte_individual(perfil_id: int, generado_por: int = None) -> Reporte:
        """Informe del estudiante: portada con su perfil, cada respuesta con lo que valió y el cierre."""
        perfil = PerfilVocacional.query.get_or_404(perfil_id)
        aplicacion = perfil.aplicacion
        usuario = aplicacion.usuario
        dj = perfil.datos_json or {}
        puntajes = dj.get('puntajes_por_area', {})

        os.makedirs(ReporteService.REPORTES_DIR, exist_ok=True)
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f'reporte_{usuario.documento or usuario.id}_{timestamp}.pdf'
        filepath = os.path.join(ReporteService.REPORTES_DIR, filename)

        nombre = f'{usuario.nombres} {usuario.apellidos}'
        doc = SimpleDocTemplate(filepath, pagesize=letter,
                                topMargin=0.6 * inch, bottomMargin=0.8 * inch,
                                leftMargin=0.8 * inch, rightMargin=0.8 * inch,
                                title=f'Informe vocacional - {nombre}',
                                author='Universidad de San Buenaventura Medellín')
        st = ReporteService._estilos()
        fecha = aplicacion.fecha_fin or aplicacion.fecha_inicio

        elements = [
            ReporteService._franja_institucional(fecha, st), Spacer(1, 16),
            ReporteService._bloque_perfil(perfil, dj, st), Spacer(1, 12),
            ReporteService._datos_estudiante(usuario, aplicacion, st), Spacer(1, 22),
        ]
        if puntajes:
            elements += ReporteService._resultados_por_area(dj, st)
        elements.append(PageBreak())

        # Las dos pruebas de la sesión: la de esta aplicación y su complementaria.
        # Intereses va primero, como en el cuestionario.
        def nombre_dimension(a):
            d = a.configuracion.instrumento.dimensiones.first()
            return d.nombre if d else ''

        complementaria = PsicometricoService._obtener_aplicacion_complementaria(aplicacion)
        pruebas = [a for a in (aplicacion, complementaria) if a]
        pruebas.sort(key=lambda a: 0 if PsicometricoService._es_interes(nombre_dimension(a)) else 1)
        for prueba in pruebas:
            es_interes = PsicometricoService._es_interes(nombre_dimension(prueba))
            elements += ReporteService._seccion_respuestas(prueba, es_interes, puntajes, st)

        elements.append(ReporteService._cierre(perfil, dj, st))

        def pie_de_pagina(canvas, doc_):
            canvas.saveState()
            canvas.setStrokeColor(LINEA)
            canvas.setLineWidth(0.6)
            canvas.line(doc_.leftMargin, 0.62 * inch, letter[0] - doc_.rightMargin, 0.62 * inch)
            canvas.setFont('Helvetica', 7.5)
            canvas.setFillColor(GRIS)
            canvas.drawString(doc_.leftMargin, 0.45 * inch,
                              f'{nombre} · Universidad de San Buenaventura Medellín · usbmed.edu.co')
            canvas.drawRightString(letter[0] - doc_.rightMargin, 0.45 * inch, f'Página {doc_.page}')
            canvas.restoreState()

        doc.build(elements, onFirstPage=pie_de_pagina, onLaterPages=pie_de_pagina)

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
