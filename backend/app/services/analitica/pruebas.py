"""Pruebas estadísticas e intervalos que usa la estadística avanzada.

Funciones puras: reciben listas o tablas y devuelven diccionarios con el
estadístico, el valor p y lo necesario para explicarlo. No tocan la base.
"""

import math

import numpy as np
from scipy import stats

Z95 = 1.959963984540054
ALFA = 0.05


def wilson(k, n, z=Z95):
    """Proporción k/n con su intervalo de Wilson al 95 %."""
    if n <= 0:
        return {'p': None, 'bajo': None, 'alto': None, 'k': k, 'n': n}
    p = k / n
    centro = (p + z * z / (2 * n)) / (1 + z * z / n)
    margen = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return {'p': p, 'bajo': max(0.0, centro - margen), 'alto': min(1.0, centro + margen), 'k': k, 'n': n}


def z_misma_muestra(k1, k2, n):
    """Diferencia entre dos categorías de la misma muestra multinomial.

    Var(p1 - p2) = [p1 + p2 - (p1 - p2)^2] / n, porque las dos proporciones
    salen de los mismos n estudiantes y no son independientes.
    """
    p1, p2 = k1 / n, k2 / n
    var = (p1 + p2 - (p1 - p2) ** 2) / n
    if var <= 0:
        return {'z': None, 'p_valor': None}
    z = (p1 - p2) / math.sqrt(var)
    return {'z': z, 'p_valor': 2 * stats.norm.sf(abs(z))}


def agrupar_para_chi2(tabla, filas, columnas, otros='Otros'):
    """Junta las columnas más chicas en "Otros" hasta cumplir la regla de Cochran.

    Regla: ninguna frecuencia esperada menor que 1 y como mucho el 20 % de las
    celdas con esperada menor que 5. Devuelve (tabla, columnas) o (None, None)
    si ni agrupando se cumple.
    """
    t = np.asarray(tabla, dtype=float)
    cols = list(columnas)
    if t.sum() == 0:
        return None, None
    # Filas y columnas vacías no aportan nada: se quitan.
    t = t[t.sum(1) > 0]
    vivas = t.sum(0) > 0
    t, cols = t[:, vivas], [c for c, v in zip(cols, vivas) if v]
    while True:
        if t.shape[0] < 2 or t.shape[1] < 2:
            return None, None
        esperada = np.outer(t.sum(1), t.sum(0)) / t.sum()
        if esperada.min() >= 1 and (esperada < 5).mean() <= 0.2:
            return t, cols
        if t.shape[1] <= 2:
            return None, None
        # Las dos columnas con menos casos se funden en "Otros".
        a, b = sorted(np.argsort(t.sum(0))[:2])
        t = np.column_stack([np.delete(t, [a, b], axis=1), t[:, a] + t[:, b]])
        cols = [c for i, c in enumerate(cols) if i not in (a, b)] + [otros]
        if cols.count(otros) > 1:
            idx = [i for i, c in enumerate(cols) if c == otros]
            t = np.column_stack([np.delete(t, idx, axis=1), t[:, idx].sum(1)])
            cols = [c for c in cols if c != otros] + [otros]


def chi2_independencia(tabla, filas, columnas):
    """Chi-cuadrado de independencia con V de Cramér, después de agrupar."""
    t, cols = agrupar_para_chi2(tabla, filas, columnas)
    if t is None:
        return None
    chi2, p, gl, esperada = stats.chi2_contingency(t, correction=False)
    n = t.sum()
    v = math.sqrt(chi2 / (n * (min(t.shape) - 1))) if n else 0.0
    return {'chi2': float(chi2), 'gl': int(gl), 'p_valor': float(p), 'v_cramer': v, 'n': int(n),
            'columnas': cols, 'tabla': t.astype(int).tolist(), 'esperada_min': float(esperada.min())}


def tamano_cramer(v, gl_min):
    """Lectura de la V de Cramér según Cohen, ajustada por grados de libertad."""
    cortes = {1: (0.10, 0.30, 0.50), 2: (0.07, 0.21, 0.35), 3: (0.06, 0.17, 0.29)}
    pequeno, mediano, grande = cortes.get(min(gl_min, 3), cortes[3])
    if v >= grande:
        return 'grande'
    if v >= mediano:
        return 'mediana'
    if v >= pequeno:
        return 'pequeña'
    return 'despreciable'


def spearman(x, y):
    if len(x) < 3:
        return None
    r = stats.spearmanr(x, y)
    rho = float(r.statistic) if not math.isnan(r.statistic) else 0.0
    return {'rho': rho, 'p_valor': float(r.pvalue) if not math.isnan(r.pvalue) else 1.0, 'n': len(x)}


def comparar_grupos(grupos):
    """ANOVA de una vía si hay varianza constante (Levene); si no, Kruskal-Wallis."""
    grupos = [np.asarray(g, dtype=float) for g in grupos if len(g) >= 2]
    if len(grupos) < 2:
        return None
    lev = stats.levene(*grupos, center='median')
    if lev.pvalue >= ALFA:
        r = stats.f_oneway(*grupos)
        prueba, estadistico = 'anova', float(r.statistic)
    else:
        r = stats.kruskal(*grupos)
        prueba, estadistico = 'kruskal', float(r.statistic)
    return {'prueba': prueba, 'estadistico': estadistico, 'p_valor': float(r.pvalue),
            'levene_p': float(lev.pvalue), 'medias': [float(g.mean()) for g in grupos],
            'n': [len(g) for g in grupos]}


def welch(a, b):
    if len(a) < 2 or len(b) < 2:
        return None
    r = stats.ttest_ind(a, b, equal_var=False)
    return {'t': float(r.statistic), 'p_valor': float(r.pvalue),
            'media_a': float(np.mean(a)), 'media_b': float(np.mean(b))}


def ecdf(valores):
    """Puntos (x, F(x)) de la función de distribución empírica."""
    x = np.sort(np.asarray(valores, dtype=float))
    n = len(x)
    return [{'x': float(v), 'f': (i + 1) / n} for i, v in enumerate(x)]


def pareto(conteos):
    """Ordena de mayor a menor y agrega la proporción acumulada."""
    total = sum(v for _, v in conteos)
    acumulado, salida = 0, []
    for nombre, v in sorted(conteos, key=lambda t: -t[1]):
        acumulado += v
        salida.append({'nombre': nombre, 'valor': v, 'acumulado': acumulado / total if total else 0})
    return salida


def minimo_chi2(filas, columnas):
    """Muestra mínima para esperar 5 casos por celda (n = 5 · filas · columnas)."""
    return 5 * filas * columnas
