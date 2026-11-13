"""Pruebas del informe PDF: filas de respuestas y dibujos (sin base de datos)."""

import io
import os
import sys
from types import SimpleNamespace as NS

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.reporte_respuestas import enunciado_corto, fila_respuesta
from app.services.reporte_graficos import Cuadros, Luz


def _binaria():
    return NS(tipo='comparacion_binaria', texto='Prefieres apoyar en la',
              escala=NS(nombre='Realista'),
              opciones={'opcion_a': {'campo': 'Realista', 'texto': 'construir'},
                        'opcion_b': {'campo': 'Artístico', 'texto': 'diseñar'}})


def _juicio():
    return NS(tipo='juicio_situacional', texto='Para entender el aumento de llegadas tarde',
              escala=NS(nombre='Investigador'),
              opciones={'opciones': [{'letra': 'A', 'puntaje': 3}, {'letra': 'B', 'puntaje': 2},
                                     {'letra': 'C', 'puntaje': 1}, {'letra': 'D', 'puntaje': 4}]})


def test_enunciado_corto_corta_en_palabra_completa():
    assert enunciado_corto('uno dos tres cuatro', 9) == 'uno dos…'
    assert enunciado_corto('  corto  ', 70) == 'corto'


def test_binaria_opcion_a_enciende_la_luz():
    f = fila_respuesta(1, _binaria(), 0)
    assert (f['tipo'], f['letra'], f['valor'], f['maximo'], f['area']) == ('luz', 'A', 1, 1, 'Realista')


def test_binaria_opcion_b_deja_la_luz_apagada():
    f = fila_respuesta(1, _binaria(), 1)
    assert (f['letra'], f['valor']) == ('B', 0)


def test_juicio_usa_el_puntaje_de_la_opcion_no_su_letra():
    assert (fila_respuesta(2, _juicio(), 1)['letra'], fila_respuesta(2, _juicio(), 1)['valor']) == ('B', 2)
    f = fila_respuesta(2, _juicio(), 3)
    assert (f['tipo'], f['letra'], f['valor'], f['maximo']) == ('cuadros', 'D', 4, 4)


def test_sin_respuesta_queda_en_cero_con_raya():
    assert (fila_respuesta(3, _juicio(), None)['letra'], fila_respuesta(3, _juicio(), None)['valor']) == ('—', 0)
    assert fila_respuesta(3, _binaria(), None)['valor'] == 0


def test_cuadros_y_luz_se_dibujan_en_un_pdf():
    from reportlab.platypus import SimpleDocTemplate, Table
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf)
    doc.build([Table([[Cuadros(3, 4, 'Realista'), Luz(True, 'Social'), Luz(False, 'Social'),
                       Cuadros(0, 4, 'Área desconocida')]])])
    assert buf.getvalue().startswith(b'%PDF')


def test_cuadros_limitan_el_valor_al_maximo():
    assert Cuadros(7, 4, 'Realista').valor == 4
    assert Cuadros(-1, 4, 'Realista').valor == 0


def test_porcentaje_combinado_suma_puntos_de_las_dos_pruebas():
    from app.services.reporte_respuestas import porcentajes_area
    d = {'interes_puntaje': 13, 'interes_maximo': 25, 'competencia_puntaje': 23, 'competencia_maximo': 32}
    assert porcentajes_area(d) == (63, 52, 72)
    assert porcentajes_area({'interes_puntaje': 5, 'interes_maximo': 10}) == (50, 50, None)
    assert porcentajes_area({}) == (0, None, None)


def test_barras_de_areas_se_dibujan():
    from reportlab.platypus import SimpleDocTemplate
    from app.services.reporte_graficos import BarrasAreas
    buf = io.BytesIO()
    filas = [('Realista', 63, 52, 72), ('Social', 60, 45, None), ('Área rara', 0, None, None)]
    SimpleDocTemplate(buf).build([BarrasAreas(filas, 400)])
    assert buf.getvalue().startswith(b'%PDF')
