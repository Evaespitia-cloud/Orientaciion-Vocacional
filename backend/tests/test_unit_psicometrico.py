"""
Pruebas Unitarias — PsicometricoService (lógica pura sin BD)
Testea la lógica de puntuación y normalización de forma aislada.
"""

import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ─── Funciones puras extraídas de PsicometricoService ─────────────────────────
# Se testea la lógica directamente sin necesidad de ORM

def calcular_puntaje_bruto(respuestas_valores, formula):
    vp = formula.get('valor_positivo', 1)
    vn = formula.get('valor_negativo', 0)
    return sum(vp if v == 1 else vn for v in respuestas_valores if v is not None)

def normalizar_puntaje(bruto, total_items, valor_positivo=1):
    maximo = total_items * valor_positivo
    return (bruto / maximo * 100) if maximo > 0 else 0

def clasificar_nivel(puntaje_normalizado):
    if puntaje_normalizado >= 80:
        return 'muy_alto'
    elif puntaje_normalizado >= 60:
        return 'alto'
    elif puntaje_normalizado >= 40:
        return 'medio'
    return 'bajo'

def determinar_perfil_dominante(puntajes_area: dict):
    if not puntajes_area:
        return None
    return max(puntajes_area, key=puntajes_area.get)

def determinar_afinidades(puntajes_area: dict, umbral: float = 0.6):
    maximo = max(puntajes_area.values()) if puntajes_area else 0
    return [area for area, p in puntajes_area.items() if p >= maximo * umbral]


def test_cargar_banco_desde_excel_saca_30_intereses_y_30_competencias(tmp_path):
    from openpyxl import Workbook
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from importar_banco_cliente import cargar_banco_desde_excel

    workbook = Workbook()
    ws_intereses = workbook.active
    ws_intereses.title = 'Intereses'
    ws_intereses.append(['Orden', 'ID', 'Par RIASEC', 'Enunciado', 'Opción A', 'Campo A', 'Opción B', 'Campo B', 'Puntaje si A', 'Puntaje si B'])
    for i in range(1, 31):
        ws_intereses.append([
            i,
            f'ITAS{i}',
            'Artístico – Social',
            f'Enunciado {i}',
            f'Opción A {i}',
            'Artístico',
            f'Opción B {i}',
            'Social',
            'Artístico=1',
            'Social=1',
        ])

    ws_competencias = workbook.create_sheet('Competencias')
    ws_competencias.append(['Orden', 'ID', 'Campo', 'Habilidad', 'Demanda', 'Dificultad', 'Contexto', 'Enunciado', 'Opción A', 'Pt A', 'Opción B', 'Pt B', 'Opción C', 'Pt C', 'Opción D', 'Pt D'])
    for i in range(1, 31):
        ws_competencias.append([
            i,
            f'REA-{i:02d}',
            'Realista',
            'Habilidad',
            'Demanda',
            'Dificultad',
            f'Contexto {i}',
            f'Enunciado {i}',
            f'Opción A {i}',
            1,
            f'Opción B {i}',
            2,
            f'Opción C {i}',
            3,
            f'Opción D {i}',
            4,
        ])

    workbook.save(tmp_path / 'Items Full day.xlsx')

    intereses, competencias = cargar_banco_desde_excel(tmp_path / 'Items Full day.xlsx')

    assert len(intereses) == 30
    assert len(competencias) == 30
    assert intereses[0]['codigo'] == 'ITAS1'
    assert competencias[0]['codigo'] == 'REA-01'


FORMULA_DEFAULT = {
    'metodo': 'suma_binaria',
    'valor_positivo': 1,
    'valor_negativo': 0,
    'umbral_afinidad': 0.6,
    'criterio_dominante': 'puntaje_maximo',
}

FORMULA_NEGATIVA = {
    'metodo': 'suma_binaria',
    'valor_positivo': 1,
    'valor_negativo': -1,
    'umbral_afinidad': 0.6,
}


def test_filtrar_intereses_excel_solo_deja_los_items_autorizados():
    from backend.app.models.instrumento import filtrar_intereses_excel_textos

    textos = [
        '¿Te gusta trabajar con herramientas, máquinas o equipos?',
        'Pregunta desviada sin aparecer en la lista Excel',
        '¿Disfrutas las actividades al aire libre o físicas?',
    ]

    assert filtrar_intereses_excel_textos(textos) == [
        '¿Te gusta trabajar con herramientas, máquinas o equipos?',
        '¿Disfrutas las actividades al aire libre o físicas?',
    ]


def test_filtrar_intereses_excel_acepta_variant_textos_del_seed_de_intereses():
    from backend.app.models.instrumento import filtrar_intereses_excel_textos

    textos = [
        '¿Te gusta trabajar con herramientas, máquinas o equipos técnicos?',
        '¿Disfrutas las actividades físicas o al aire libre?',
        '¿Te gustaría trabajar en ingeniería, mecánica o construcción?',
        '¿Te gusta la contabilidad, la administración o el archivo de documentos?',
        'Pregunta desviada sin aparecer en la lista Excel',
    ]

    assert filtrar_intereses_excel_textos(textos) == [
        '¿Te gusta trabajar con herramientas, máquinas o equipos técnicos?',
        '¿Disfrutas las actividades físicas o al aire libre?',
        '¿Te gustaría trabajar en ingeniería, mecánica o construcción?',
        '¿Te gusta la contabilidad, la administración o el archivo de documentos?',
    ]


def test_cargar_banco_desde_pdfs_saca_30_intereses_y_30_competencias():
    from pathlib import Path
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from importar_banco_cliente import cargar_banco_desde_pdfs

    intereses, competencias = cargar_banco_desde_pdfs(
        Path('Intereses.pdf'),
        Path('Competencias.pdf'),
    )

    assert len(intereses) == 30
    assert len(competencias) == 30
    assert intereses[0]['codigo'].startswith('IT')
    assert competencias[0]['codigo'].startswith('REA')


# ─── UT-04: Cálculo de puntaje bruto ──────────────────────────────────────────
class TestCalculoPuntajeBruto:
    def test_todas_positivas(self):
        respuestas = [1, 1, 1, 1, 1]
        assert calcular_puntaje_bruto(respuestas, FORMULA_DEFAULT) == 5

    def test_todas_negativas(self):
        respuestas = [0, 0, 0]
        assert calcular_puntaje_bruto(respuestas, FORMULA_DEFAULT) == 0

    def test_mixto(self):
        respuestas = [1, 0, 1, 0, 1]
        assert calcular_puntaje_bruto(respuestas, FORMULA_DEFAULT) == 3

    def test_con_ninguna_respuesta(self):
        assert calcular_puntaje_bruto([], FORMULA_DEFAULT) == 0

    def test_ignora_valores_none(self):
        respuestas = [1, None, 1, None]
        assert calcular_puntaje_bruto(respuestas, FORMULA_DEFAULT) == 2

    def test_formula_con_valor_negativo(self):
        respuestas = [1, 0, 1]
        assert calcular_puntaje_bruto(respuestas, FORMULA_NEGATIVA) == 1  # 1+(-1)+1


# ─── UT-05: Normalización de puntaje ─────────────────────────────────────────
class TestNormalizacion:
    def test_maximo(self):
        assert normalizar_puntaje(10, 10) == 100.0

    def test_cero(self):
        assert normalizar_puntaje(0, 10) == 0.0

    def test_mitad(self):
        assert normalizar_puntaje(5, 10) == 50.0

    def test_sin_items(self):
        assert normalizar_puntaje(5, 0) == 0.0


# ─── UT-06: Clasificación de nivel ───────────────────────────────────────────
class TestClasificacionNivel:
    @pytest.mark.parametrize('puntaje,nivel', [
        (80, 'muy_alto'),
        (100, 'muy_alto'),
        (60, 'alto'),
        (75, 'alto'),
        (40, 'medio'),
        (59, 'medio'),
        (0, 'bajo'),
        (39, 'bajo'),
    ])
    def test_clasificacion(self, puntaje, nivel):
        assert clasificar_nivel(puntaje) == nivel


# ─── UT-07: Perfil dominante y afinidades ─────────────────────────────────────
class TestPerfilDominante:
    def test_dominante_claro(self):
        p = {'Social': 80, 'Realista': 40, 'Artístico': 30}
        assert determinar_perfil_dominante(p) == 'Social'

    def test_afinidades_con_umbral_60(self):
        # 80 * 0.6 = 48; Social=80 ✓, Investigador=50 ✓ (50>=48), Emprendedor=60 ✓
        p = {'Social': 80, 'Investigador': 50, 'Emprendedor': 60}
        afs = determinar_afinidades(p, 0.6)
        assert 'Social' in afs
        assert 'Emprendedor' in afs
        assert 'Investigador' in afs  # 50 >= 48 → califica
        # Verificar que un valor bajo (40 < 48) NO califica
        afs2 = determinar_afinidades({'Social': 80, 'Investigador': 40, 'Emprendedor': 60}, 0.6)
        assert 'Investigador' not in afs2  # 40 < 48

    def test_dict_vacio(self):
        assert determinar_perfil_dominante({}) is None

    def test_todos_igual(self):
        p = {'R': 50, 'I': 50, 'A': 50}
        # Con empate, max() retorna el primero encontrado — solo verificamos que retorne algo
        assert determinar_perfil_dominante(p) in ('R', 'I', 'A')
