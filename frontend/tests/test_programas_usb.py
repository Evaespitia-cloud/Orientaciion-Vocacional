"""Pruebas del módulo compartido de programas USB (lógica pura, sin servidor)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.programas_usb import (
    PROGRAMAS, PROGRAMAS_POR_PERFIL, campos_de, programas_recomendados, programas_para_mapa,
    definicion_perfil, sesiones_distintas, recomendaciones_accionables,
)


def _puntajes(**valores):
    nombres = {'R': 'Realista', 'I': 'Investigador', 'A': 'Artístico',
               'S': 'Social', 'E': 'Emprendedor', 'C': 'Convencional'}
    return {nombres[k]: {'normalizado': v} for k, v in valores.items()}








def test_hay_18_programas_y_cada_uno_pertenece_a_algun_campo():
    assert len(PROGRAMAS) == 18
    for p in PROGRAMAS:
        assert campos_de(p['n']), p['n']


def test_la_lista_por_perfil_es_la_misma_del_backend():
    import ast
    ruta = os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'app', 'services', 'psicometrico_service.py')
    fuente = open(ruta, encoding='utf-8').read()
    inicio = fuente.index('PROGRAMAS_POR_PERFIL = {')
    fin = fuente.index('\n}', inicio) + 2
    del_backend = ast.literal_eval(fuente[inicio:fin].split('=', 1)[1].strip())
    assert PROGRAMAS_POR_PERFIL == del_backend


def test_recomendados_principal_primero_y_sin_repetir():
    lista = programas_recomendados('Emprendedor', 'Convencional')
    nombres = [p['n'] for p in lista]
    assert nombres[:4] == PROGRAMAS_POR_PERFIL['Emprendedor']
    assert nombres.count('Administración de Negocios') == 1
    assert [p['grupo'] for p in lista].count('secundario') == 3
    assert lista[0]['url'].startswith('https://usbmed.edu.co/programas/pregrados/')
    assert 'af' not in lista[0] and 's' not in lista[0]


def test_recomendados_sin_secundario_ni_perfil_conocido():
    assert [p['grupo'] for p in programas_recomendados('Convencional')] == ['principal'] * 4
    assert programas_recomendados('Sin determinar') == []


def test_mapa_marca_grupos_y_conserva_el_orden():
    mapa = programas_para_mapa('Realista', 'Convencional')
    assert [p['n'] for p in mapa] == [p['n'] for p in PROGRAMAS]
    grupos = {p['n']: p['grupo'] for p in mapa}
    assert grupos['Ingeniería Industrial'] == 'principal'
    assert grupos['Contaduría Pública'] == 'secundario'
    assert grupos['Psicología'] == 'otro'
    assert {p['n']: p['campos'] for p in mapa}['Ingeniería Industrial'] == ['Realista', 'Convencional']


def test_perfil_marcado_con_un_campo_lejos_del_resto():
    d = definicion_perfil(_puntajes(E=100, C=87.5, S=37.5, I=37.5, A=29.2, R=12.5))
    assert d == {'tipo': 'marcado', 'areas': ['Emprendedor']}


def test_perfil_marcado_en_dos_campos():
    d = definicion_perfil(_puntajes(R=80, I=75, A=40, S=30, E=20, C=10))
    assert d == {'tipo': 'marcado', 'areas': ['Realista', 'Investigador']}


def test_perfil_equilibrado_con_tres_o_mas_campos_cerca():
    d = definicion_perfil(_puntajes(R=63.2, I=51.9, A=63.4, S=60.0, E=43.3, C=63.2))
    assert d['tipo'] == 'equilibrado'
    assert d['areas'][0] == 'Artístico'
    assert set(d['areas']) == {'Artístico', 'Realista', 'Convencional', 'Social'}


def test_definicion_sin_puntajes_es_none():
    assert definicion_perfil({}) is None


def test_sesiones_distintas_cuenta_fechas_no_aplicaciones():
    historial = [{'fecha': '2026-09-23'}, {'fecha': '2026-09-23'}, {'fecha': None}]
    assert sesiones_distintas(historial) == 1
    historial.append({'fecha': '2027-03-01'})
    assert sesiones_distintas(historial) == 2


def test_recomendaciones_quita_las_repetidas_y_deja_las_accionables():
    descripcion = 'Tienes una fuerte inclinación hacia actividades prácticas.'
    texto = '\n'.join([
        'Tu perfil vocacional Holland es: Realista (Código RIASEC: RCI).',
        descripcion,
        'Programas de pregrado de la USB afines a tu perfil: Ingeniería Industrial.',
        'Tu perfil secundario es Convencional. En la USB también podrías explorar: Contaduría.',
        'Ambientes de trabajo ideales: Talleres.',
        'Se recomienda hablar con el orientador escolar o consejero de tu institución.',
        'Aún no has completado la prueba de Intereses; tu perfil integrado se actualizará cuando la realices.',
    ])
    assert recomendaciones_accionables(texto, descripcion) == [
        'Aún no has completado la prueba de Intereses; tu perfil integrado se actualizará cuando la realices.',
    ]


def test_fortalezas_quitan_el_porcentaje_del_backend():
    from app.programas_usb import fortalezas_sin_porcentaje
    texto = ('• Convencional (62%): Organización, precisión\n'
             '\n'
             '• Realista (62%): Habilidad manual\n'
             'Línea sin formato')
    assert fortalezas_sin_porcentaje(texto) == [
        ('Convencional', 'Organización, precisión'),
        ('Realista', 'Habilidad manual'),
        ('', 'Línea sin formato'),
    ]


def test_areas_de_mayor_a_menor_y_empates_en_el_orden_del_perfil():
    from app.programas_usb import areas_por_porcentaje
    puntajes = _puntajes(R=63, I=52, A=63, S=60, E=43, C=63)
    ranking = ['Realista', 'Convencional', 'Investigador', 'Social', 'Artístico', 'Emprendedor']
    assert areas_por_porcentaje(puntajes, ranking) == [
        'Realista', 'Convencional', 'Artístico', 'Social', 'Investigador', 'Emprendedor']
    assert areas_por_porcentaje(_puntajes(R=10, I=90), [])[:2] == ['Investigador', 'Realista']
