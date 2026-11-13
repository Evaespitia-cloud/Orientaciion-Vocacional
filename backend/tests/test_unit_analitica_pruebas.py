"""Pruebas de las funciones estadísticas: contra scipy y contra casos hechos a mano."""

import math

import numpy as np
import pytest
from scipy import stats

from app.services.analitica import pruebas as pr


def test_wilson_caso_a_mano():
    # 30 de 100: centro 0,3074, margen 0,0885 -> [0,2189 ; 0,3959]
    r = pr.wilson(30, 100)
    assert r['p'] == 0.3
    assert r['bajo'] == pytest.approx(0.2189, abs=1e-4)
    assert r['alto'] == pytest.approx(0.3959, abs=1e-4)


def test_wilson_sin_muestra():
    assert pr.wilson(0, 0)['p'] is None


def test_z_misma_muestra():
    # p1 = 0,4 y p2 = 0,2 con n = 100: var = (0,6 - 0,04)/100 -> z = 0,2/0,0748 = 2,673
    r = pr.z_misma_muestra(40, 20, 100)
    assert r['z'] == pytest.approx(2.6726, abs=1e-3)
    assert r['p_valor'] == pytest.approx(2 * stats.norm.sf(2.6726), abs=1e-4)


def test_chi2_igual_que_scipy_cuando_no_hay_que_agrupar():
    tabla = [[30, 20, 25], [20, 30, 25]]
    r = pr.chi2_independencia(tabla, ['F', 'M'], ['R', 'I', 'A'])
    chi2, p, gl, _ = stats.chi2_contingency(np.array(tabla), correction=False)
    assert r['chi2'] == pytest.approx(chi2) and r['p_valor'] == pytest.approx(p) and r['gl'] == gl
    assert r['v_cramer'] == pytest.approx(math.sqrt(chi2 / 150))
    assert r['columnas'] == ['R', 'I', 'A']


def test_chi2_agrupa_columnas_chicas_en_otros():
    # A y S tienen esperadas cercanas a 3: se funden y "Otros" queda con esperada 5,5.
    tabla = [[40, 30, 3, 3], [35, 38, 3, 2]]
    r = pr.chi2_independencia(tabla, ['F', 'M'], ['R', 'I', 'A', 'S'])
    assert r['columnas'] == ['R', 'I', 'Otros']
    assert r['tabla'] == [[40, 30, 6], [35, 38, 5]]
    assert r['esperada_min'] >= 1


def test_chi2_sin_datos_suficientes():
    assert pr.chi2_independencia([[1, 0], [0, 1]], ['a', 'b'], ['x', 'y']) is None
    assert pr.chi2_independencia([[0, 0], [0, 0]], ['a', 'b'], ['x', 'y']) is None


def test_comparar_grupos_usa_anova_con_varianzas_parecidas():
    rng = np.random.default_rng(1)
    g = [rng.normal(50, 10, 40), rng.normal(55, 10, 40), rng.normal(60, 10, 40)]
    r = pr.comparar_grupos(g)
    assert r['prueba'] == 'anova'
    assert r['p_valor'] == pytest.approx(stats.f_oneway(*g).pvalue)


def test_comparar_grupos_cae_a_kruskal_sin_varianza_constante():
    rng = np.random.default_rng(2)
    g = [rng.normal(50, 1, 60), rng.normal(50, 25, 60)]
    r = pr.comparar_grupos(g)
    assert r['prueba'] == 'kruskal'
    assert r['p_valor'] == pytest.approx(stats.kruskal(*g).pvalue)


def test_spearman_y_welch_como_scipy():
    x, y = [1, 2, 3, 4, 5, 6], [2, 1, 4, 3, 6, 5]
    assert pr.spearman(x, y)['rho'] == pytest.approx(stats.spearmanr(x, y).statistic)
    a, b = [1, 2, 3, 4], [3, 4, 5, 9]
    assert pr.welch(a, b)['p_valor'] == pytest.approx(stats.ttest_ind(a, b, equal_var=False).pvalue)


def test_ecdf_y_pareto():
    assert pr.ecdf([3, 1, 2]) == [{'x': 1.0, 'f': 1 / 3}, {'x': 2.0, 'f': 2 / 3}, {'x': 3.0, 'f': 1.0}]
    p = pr.pareto([('a', 1), ('b', 6), ('c', 3)])
    assert [x['nombre'] for x in p] == ['b', 'c', 'a']
    assert p[1]['acumulado'] == pytest.approx(0.9)


@pytest.mark.parametrize('v, lectura', [(0.05, 'despreciable'), (0.12, 'pequeña'), (0.31, 'mediana'), (0.6, 'grande')])
def test_tamano_cramer(v, lectura):
    assert pr.tamano_cramer(v, 1) == lectura
