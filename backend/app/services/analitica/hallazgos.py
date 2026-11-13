"""Hallazgos de la estadística avanzada.

Cada función recibe la tabla de análisis (una fila por estudiante) y devuelve
una tarjeta: la conclusión en palabras simples, la gráfica que la sostiene y el
método (pasos, fórmulas, supuestos y resultado) para el botón de ayuda. Si la
muestra no alcanza, la tarjeta dice cuántas encuestas faltan.
"""

from collections import Counter

import numpy as np
from scipy import stats

from ...models.escolar import SedeEducativa
from . import pruebas as pr
from .datos import AREAS

ALFA = pr.ALFA


# ─── Formato ──────────────────────────────────────────────────────────────── #

def pct(x, dec=0):
    return 'sin dato' if x is None else f'{x * 100:.{dec}f}'.replace('.', ',') + ' %'


def num(x, dec=2):
    return f'{x:.{dec}f}'.replace('.', ',')


def valor_p(p):
    return 'p < 0,001' if p < 0.001 else f'p = {num(p, 3)}'


def lista(nombres):
    nombres = list(nombres)
    if len(nombres) <= 1:
        return ''.join(nombres)
    return ', '.join(nombres[:-1]) + ' y ' + nombres[-1]


UNIDADES = {
    'encuestas completas': 'encuesta completa',
    'encuestas en el grupo más pequeño': 'encuesta en el grupo más pequeño',
    'encuestas en el grado con menos': 'encuesta en el grado con menos',
    'estudiantes con dirección en el sector con menos': 'estudiante con dirección en el sector con menos',
    'estudiantes que repitan el test': 'estudiante que repita el test',
    'estudiante con colegio': 'estudiante con colegio',
}


def faltan_texto(faltan, unidad):
    if faltan == 1:
        return f'Falta 1 {UNIDADES.get(unidad, unidad)} para poder concluir.'
    plural = {v: k for k, v in UNIDADES.items()}.get(unidad, unidad)
    if unidad == 'estudiante con colegio':
        plural = 'estudiantes con colegio'
    return f'Faltan {faltan} {plural} para poder concluir.'


def tarjeta(id_, pregunta, n, minimo, metodo, conclusion=None, estado=None, grafica=None, detalle=None,
            unidad='encuestas completas'):
    faltan = max(0, minimo - n)
    if faltan:
        return {'id': id_, 'pregunta': pregunta, 'estado': 'faltan_datos', 'n': n, 'minimo': minimo,
                'faltan': faltan, 'conclusion': faltan_texto(faltan, unidad),
                'detalle': f'Hay {n} de las {minimo} necesarias.', 'grafica': None, 'metodo': metodo}
    return {'id': id_, 'pregunta': pregunta, 'estado': estado or 'concluye', 'n': n, 'minimo': minimo,
            'faltan': 0, 'conclusion': conclusion, 'detalle': detalle, 'grafica': grafica, 'metodo': metodo}


def completos(filas):
    return [f for f in filas if f['completo']]


def tabla_contingencia(filas, clave, categorias=None):
    grupos = categorias or sorted({f[clave] for f in filas if f[clave] not in (None, '')})
    tabla = [[sum(1 for f in filas if f[clave] == g and f['principal'] == a) for a in AREAS] for g in grupos]
    return grupos, tabla


def barras_apiladas(grupos, tabla):
    return {'tipo': 'apiladas', 'grupos': grupos, 'areas': AREAS,
            'valores': [[c / sum(fila) if sum(fila) else 0 for c in fila] for fila in tabla],
            'totales': [sum(fila) for fila in tabla]}


def mayor_diferencia(grupos, tabla, columnas):
    """La columna donde más se separan dos grupos, para contar la diferencia en palabras."""
    props = np.array([[c / sum(f) for c in f] for f in tabla])
    mejor = None
    for j, col in enumerate(columnas):
        if col == 'Otros':
            continue
        hi, lo = int(props[:, j].argmax()), int(props[:, j].argmin())
        dif = props[hi, j] - props[lo, j]
        if mejor is None or dif > mejor[0]:
            mejor = (dif, col, grupos[hi], props[hi, j], grupos[lo], props[lo, j])
    return mejor


def metodo_chi2(grupo, filas_txt):
    return {
        'pasos': [
            f'Se cruza el perfil principal de cada estudiante con su {grupo} en una tabla de frecuencias.',
            'Si una celda espera menos de 5 casos, los perfiles con menos estudiantes se juntan en "Otros" '
            '(regla de Cochran: ninguna esperada menor que 1 y como mucho el 20 % por debajo de 5).',
            'Se compara lo observado con lo que se esperaría si el perfil no dependiera del ' + grupo + '.',
            'La V de Cramér dice qué tan fuerte es la relación, de 0 (ninguna) a 1 (total).',
        ],
        'formulas': [r'E_{ij} = \frac{F_i \, C_j}{n}',
                     r'\chi^2 = \sum_{i,j} \frac{(O_{ij} - E_{ij})^2}{E_{ij}}',
                     r'V = \sqrt{\frac{\chi^2}{n\,(\min(f, c) - 1)}}'],
        'supuestos': 'Cada estudiante cuenta una sola vez y las respuestas de uno no dependen de las de otro. '
                     + filas_txt,
    }


# ─── H1. Campos dominantes ────────────────────────────────────────────────── #

def h_campos(filas):
    f = completos(filas)
    n = len(f)
    metodo = {
        'pasos': ['Se cuenta cuántos estudiantes tienen cada campo como perfil principal.',
                  'A cada proporción se le calcula su intervalo de confianza de Wilson al 95 %.',
                  'Se comparan los dos primeros con una prueba z para dos categorías de la misma muestra.'],
        'formulas': [r'\hat p = \frac{k}{n}',
                     r'\frac{\hat p + \frac{z^2}{2n} \pm z\sqrt{\frac{\hat p(1-\hat p)}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}',
                     r'z = \frac{\hat p_1 - \hat p_2}{\sqrt{\left[\hat p_1 + \hat p_2 - (\hat p_1 - \hat p_2)^2\right]/n}}'],
        'supuestos': 'Las dos proporciones salen de los mismos estudiantes, por eso la varianza de la diferencia '
                     'no es la de dos muestras independientes.',
    }
    if n < 30:
        return tarjeta('campos', '¿Hacia qué campos se inclinan?', n, 30, metodo)
    conteo = Counter(x['principal'] for x in f)
    ic = {a: pr.wilson(conteo.get(a, 0), n) for a in AREAS}
    orden = sorted(AREAS, key=lambda a: -conteo.get(a, 0))
    a, b = orden[0], orden[1]
    z = pr.z_misma_muestra(conteo.get(a, 0), conteo.get(b, 0), n)
    if z['p_valor'] is not None and z['p_valor'] < ALFA:
        conclusion = (f'{a} es el campo que más aparece: {pct(ic[a]["p"])} de los estudiantes, '
                      f'claramente por encima de {b} ({pct(ic[b]["p"])}).')
        estado = 'concluye'
    else:
        conclusion = (f'{a} y {b} están empatados como campos más comunes ({pct(ic[a]["p"])} y '
                      f'{pct(ic[b]["p"])}); con {n} estudiantes la diferencia no es clara.')
        estado = 'sin_evidencia'
    metodo['resultado'] = (f'{a}: {pct(ic[a]["p"], 1)} [{pct(ic[a]["bajo"], 1)} ; {pct(ic[a]["alto"], 1)}]. '
                           f'{b}: {pct(ic[b]["p"], 1)}. z = {num(z["z"])}, {valor_p(z["p_valor"])}.')
    grafica = {'tipo': 'proporciones', 'areas': orden,
               'valores': [ic[x]['p'] for x in orden], 'bajo': [ic[x]['bajo'] for x in orden],
               'alto': [ic[x]['alto'] for x in orden]}
    return tarjeta('campos', '¿Hacia qué campos se inclinan?', n, 30, metodo, conclusion, estado, grafica,
                   f'{n} estudiantes con las dos pruebas.')


# ─── H2. Gusto frente a habilidad ─────────────────────────────────────────── #

def h_gusto_habilidad(filas):
    f = completos(filas)
    n = len(f)
    metodo = {
        'pasos': ['Para cada campo se toman el % de Intereses y el % de Competencias de cada estudiante.',
                  'Se mide con la correlación de Spearman si quien más disfruta un campo también se siente más capaz en él.',
                  'Se corrige por hacer seis pruebas a la vez (Bonferroni: cada una se juzga con 0,05 / 6).',
                  'Aparte, se cuenta cuántos tienen el mismo campo en el primer lugar de las dos pruebas '
                  'y se compara con lo que daría el azar (1 de 6) con una prueba binomial.'],
        'formulas': [r'\rho = 1 - \frac{6\sum d_i^2}{n(n^2 - 1)}', r'\alpha^{*} = \frac{0{,}05}{6}'],
        'supuestos': 'Spearman usa rangos, así que no exige que los porcentajes sigan una distribución normal.',
    }
    if n < 20:
        return tarjeta('gusto', '¿Lo que les gusta coincide con lo que saben hacer?', n, 20, metodo)
    rhos = {}
    for a in AREAS:
        r = pr.spearman([x['interes'][a] for x in f], [x['competencia'][a] for x in f])
        rhos[a] = r
    alfa6 = ALFA / 6
    van_juntos = [a for a in AREAS if rhos[a]['rho'] > 0 and rhos[a]['p_valor'] < alfa6]
    sin_relacion = [a for a in AREAS if a not in van_juntos]
    coinciden = sum(1 for x in f if max(x['interes'], key=x['interes'].get) == max(x['competencia'], key=x['competencia'].get))
    binom = stats.binomtest(coinciden, n, 1 / 6)
    if van_juntos:
        conclusion = (f'En {lista(van_juntos)}, a quien más le gusta también se siente más capaz. '
                      + (f'En {lista(sin_relacion)} el gusto va sin la habilidad: ahí conviene reforzar.' if sin_relacion else ''))
        estado = 'concluye'
    else:
        conclusion = 'En ningún campo el gusto y la habilidad van de la mano: lo que les atrae no es donde se sienten más capaces.'
        estado = 'concluye' if n >= 60 else 'sin_evidencia'
    detalle = (f'{pct(coinciden / n)} tiene el mismo campo de primero en las dos pruebas '
               f'(al azar sería {pct(1 / 6)}).')
    metodo['resultado'] = ' · '.join(f'{a}: ρ = {num(rhos[a]["rho"])} ({valor_p(rhos[a]["p_valor"])})' for a in AREAS) \
        + f'. Coincidencia del primer lugar: {coinciden} de {n}, prueba binomial {valor_p(binom.pvalue)}.'
    grafica = {'tipo': 'correlaciones', 'areas': AREAS, 'valores': [rhos[a]['rho'] for a in AREAS],
               'significativo': [a in van_juntos for a in AREAS]}
    return tarjeta('gusto', '¿Lo que les gusta coincide con lo que saben hacer?', n, 20, metodo, conclusion,
                   estado, grafica, detalle)


# ─── H3. Qué tan definidos están ──────────────────────────────────────────── #

def h_definicion(filas):
    f = completos(filas)
    n = len(f)
    metodo = {
        'pasos': ['Para cada estudiante se cuentan los campos que quedan a menos de 10 puntos de su primer campo '
                  '(contando el primero).',
                  'Con 3 o más, el perfil es equilibrado, la misma regla que ve el estudiante en sus resultados.',
                  'La proporción de perfiles equilibrados lleva su intervalo de Wilson al 95 %.'],
        'formulas': [r'c_i = \#\{\,a : P_{1,i} - P_{a,i} < 10\,\}', r'\text{equilibrado} \iff c_i \ge 3'],
        'supuestos': 'Se usa el porcentaje combinado de Intereses y Competencias de cada campo.',
    }
    if n < 30:
        return tarjeta('definicion', '¿Qué tan definidos están sus perfiles?', n, 30, metodo)
    cercanos = []
    for x in f:
        top = max(x['combinado'].values())
        cercanos.append(sum(1 for v in x['combinado'].values() if top - v < 10))
    equil = sum(1 for c in cercanos if c >= 3)
    ic = pr.wilson(equil, n)
    conclusion = (f'{pct(ic["p"])} tiene un perfil equilibrado, con tres o más campos casi empatados: '
                  f'son quienes más necesitan acompañamiento para decidir.')
    metodo['resultado'] = f'{equil} de {n} equilibrados: {pct(ic["p"], 1)} [{pct(ic["bajo"], 1)} ; {pct(ic["alto"], 1)}].'
    dist = Counter(cercanos)
    grafica = {'tipo': 'barras', 'etiquetas': [str(k) for k in range(1, 7)],
               'valores': [dist.get(k, 0) for k in range(1, 7)], 'marca_desde': 3,
               'eje_x': 'Campos a menos de 10 puntos del primero', 'eje_y': 'Estudiantes'}
    return tarjeta('definicion', '¿Qué tan definidos están sus perfiles?', n, 30, metodo, conclusion, 'concluye',
                   grafica, f'Intervalo del 95 %: entre {pct(ic["bajo"])} y {pct(ic["alto"])}.')


# ─── H4, H5, H7, H9. Perfil según un grupo (chi-cuadrado) ─────────────────── #

def _perfil_por_grupo(filas, id_, pregunta, clave, nombre_grupo, categorias=None, etiquetas=None, extra=None):
    f = [x for x in completos(filas) if x[clave] not in (None, '')]
    grupos, tabla = tabla_contingencia(f, clave, categorias)
    grupos_validos = [g for g, fila in zip(grupos, tabla) if sum(fila)]
    minimo = pr.minimo_chi2(max(2, len(grupos_validos)), 6)
    metodo = metodo_chi2(nombre_grupo, extra or '')
    n = len(f)
    if n < minimo:
        return tarjeta(id_, pregunta, n, minimo, metodo)
    r = pr.chi2_independencia(tabla, grupos, AREAS)
    nombres = [etiquetas.get(g, g) if etiquetas else g for g in grupos]
    grafica = barras_apiladas(nombres, tabla)
    if r is None:
        return tarjeta(id_, pregunta, n, n + 30, metodo)
    tam = pr.tamano_cramer(r['v_cramer'], min(len(r['tabla']), len(r['columnas'])) - 1)
    metodo['resultado'] = (f'χ² = {num(r["chi2"])}, gl = {r["gl"]}, {valor_p(r["p_valor"])}, '
                           f'V de Cramér = {num(r["v_cramer"])} ({tam}). Columnas: {", ".join(r["columnas"])}.')
    if r['p_valor'] < ALFA and tam != 'despreciable':
        dif = mayor_diferencia([etiquetas.get(g, g) if etiquetas else g for g, fila in zip(grupos, tabla) if sum(fila)],
                               r['tabla'], r['columnas'])
        conclusion = (f'El perfil sí cambia según el {nombre_grupo}: {dif[1]} pesa {pct(dif[3])} en {dif[2]} '
                      f'frente a {pct(dif[5])} en {dif[4]}.')
        estado = 'concluye'
    else:
        conclusion = (f'No hay evidencia de que el perfil cambie según el {nombre_grupo}: '
                      f'las proporciones son parecidas entre grupos.')
        estado = 'sin_evidencia'
    return tarjeta(id_, pregunta, n, minimo, metodo, conclusion, estado, grafica,
                   f'{n} estudiantes; relación {tam} (V = {num(r["v_cramer"])}).')


def h_genero(filas):
    return _perfil_por_grupo(filas, 'genero', '¿Influye el género?', 'genero', 'género',
                             categorias=['Femenino', 'Masculino'],
                             extra='Se dejan por fuera quienes prefirieron no decir su género.')


def h_estrato(filas):
    grupos = {1: '1 y 2', 2: '1 y 2', 3: '3 y 4', 4: '3 y 4', 5: '5 y 6', 6: '5 y 6'}
    f = [dict(x, estrato_grupo=grupos.get(x['estrato'])) for x in filas]
    t = _perfil_por_grupo(f, 'estrato', '¿Influye el estrato?', 'estrato_grupo', 'estrato',
                          categorias=['1 y 2', '3 y 4', '5 y 6'],
                          extra='El estrato sale de la dirección del estudiante (el estrato de los medidores '
                                'residenciales de esa dirección). Se agrupa de a dos para tener casos suficientes.')
    t['metodo']['pasos'].insert(0, 'El estrato no se le pregunta al estudiante: sale de la dirección que escribió al registrarse.')
    return t


def h_municipio(filas):
    cuenta = Counter(x['municipio'] for x in completos(filas) if x['municipio'])
    grandes = [m for m, c in cuenta.most_common() if c >= 20]
    etiquetas = {m: m.title().replace('Medellin', 'Medellín').replace('Itagui', 'Itagüí') for m in cuenta}
    f = [dict(x, municipio_grupo=None if not x['municipio'] else (x['municipio'] if x['municipio'] in grandes else 'OTROS'))
         for x in filas]
    etiquetas['OTROS'] = 'Otros municipios'
    return _perfil_por_grupo(f, 'municipio', '¿Dónde están los perfiles?', 'municipio_grupo', 'municipio',
                             categorias=grandes + (['OTROS'] if len(cuenta) > len(grandes) else []),
                             etiquetas=etiquetas,
                             extra='Los municipios con menos de 20 estudiantes se juntan en "Otros municipios".')


# ─── H5 y H6. Porcentaje por área entre grupos ────────────────────────────── #

def h_sector(filas):
    f = [x for x in completos(filas) if x['sector'] in ('Oficial', 'Privado')]
    of = [x for x in f if x['sector'] == 'Oficial']
    pv = [x for x in f if x['sector'] == 'Privado']
    metodo = {
        'pasos': ['Se separan los estudiantes de colegios oficiales y privados (el sector sale del catálogo de colegios).',
                  'En cada campo se comparan los promedios del % combinado con la t de Welch, que no supone varianzas iguales.',
                  'Se corrige por las seis comparaciones (Bonferroni).'],
        'formulas': [r't = \frac{\bar x_1 - \bar x_2}{\sqrt{\frac{s_1^2}{n_1} + \frac{s_2^2}{n_2}}}', r'\alpha^{*} = \frac{0{,}05}{6}'],
        'supuestos': 'Con 20 o más estudiantes por grupo el promedio se comporta como normal aunque los datos no lo sean.',
    }
    n = min(len(of), len(pv))
    if n < 20:
        return tarjeta('sector', '¿Cambia entre colegios oficiales y privados?', n, 20, metodo,
                       unidad='encuestas en el grupo más pequeño')
    res = {a: pr.welch([x['combinado'][a] for x in of], [x['combinado'][a] for x in pv]) for a in AREAS}
    signif = [a for a in AREAS if res[a]['p_valor'] < ALFA / 6]
    if signif:
        partes = [f'{a} es {num(abs(res[a]["media_b"] - res[a]["media_a"]), 0)} puntos más alto en los '
                  f'{"privados" if res[a]["media_b"] > res[a]["media_a"] else "oficiales"}' for a in signif]
        conclusion = 'Sí hay brechas por tipo de colegio: ' + lista(partes) + '.'
        estado = 'concluye'
    else:
        conclusion = 'Los estudiantes de colegios oficiales y privados muestran perfiles parecidos en los seis campos.'
        estado = 'sin_evidencia'
    metodo['resultado'] = ' · '.join(f'{a}: {num(res[a]["media_a"], 1)} frente a {num(res[a]["media_b"], 1)} '
                                     f'({valor_p(res[a]["p_valor"])})' for a in AREAS)
    grafica = {'tipo': 'agrupadas', 'areas': AREAS, 'series': [
        {'nombre': f'Oficiales ({len(of)})', 'valores': [res[a]['media_a'] for a in AREAS]},
        {'nombre': f'Privados ({len(pv)})', 'valores': [res[a]['media_b'] for a in AREAS]}], 'eje_y': '% combinado promedio'}
    t = tarjeta('sector', '¿Cambia entre colegios oficiales y privados?', n, 20, metodo, conclusion, estado,
                grafica, f'{len(of)} estudiantes de colegios oficiales y {len(pv)} de privados.',
                unidad='encuestas en el grupo más pequeño')
    t['n_total'] = len(f)
    return t


def h_grado(filas):
    grados = ['9°', '10°', '11°']
    f = [x for x in completos(filas) if x['grado'] in grados]
    por = {g: [x for x in f if x['grado'] == g] for g in grados}
    metodo = {
        'pasos': ['Se agrupan los estudiantes por grado.',
                  'En cada campo se revisa con la prueba de Levene si la varianza es constante entre grados.',
                  'Si lo es, se comparan los promedios con ANOVA de una vía; si no, con Kruskal-Wallis, que usa rangos.',
                  'Se corrige por las seis comparaciones (Bonferroni).'],
        'formulas': [r'F = \frac{\sum_g n_g(\bar x_g - \bar x)^2/(k-1)}{\sum_g \sum_i (x_{gi} - \bar x_g)^2/(n-k)}',
                     r'H = \frac{12}{n(n+1)}\sum_g \frac{R_g^2}{n_g} - 3(n+1)'],
        'supuestos': 'Se necesitan al menos 10 estudiantes en cada grado.',
    }
    n = min(len(v) for v in por.values())
    if n < 10:
        return tarjeta('grado', '¿Cambia entre 9°, 10° y 11°?', n, 10, metodo, unidad='encuestas en el grado con menos')
    res = {a: pr.comparar_grupos([[x['combinado'][a] for x in por[g]] for g in grados]) for a in AREAS}
    signif = [a for a in AREAS if res[a]['p_valor'] < ALFA / 6]
    medias = {a: res[a]['medias'] for a in AREAS}
    if signif:
        partes = [f'{a} {"sube" if medias[a][2] > medias[a][0] else "baja"} '
                  f'{num(abs(medias[a][2] - medias[a][0]), 0)} puntos de 9° a 11°' for a in signif]
        conclusion = 'El perfil cambia con el grado: ' + lista(partes) + '.'
        estado = 'concluye'
    else:
        conclusion = 'Los perfiles son parecidos en 9°, 10° y 11°: la orientación puede empezar desde 9° con la misma base.'
        estado = 'sin_evidencia'
    metodo['resultado'] = ' · '.join(f'{a}: {"ANOVA" if res[a]["prueba"] == "anova" else "Kruskal-Wallis"} '
                                     f'{valor_p(res[a]["p_valor"])}' for a in AREAS)
    grafica = {'tipo': 'agrupadas', 'areas': AREAS, 'eje_y': '% combinado promedio',
               'series': [{'nombre': f'{g} ({len(por[g])})', 'valores': [medias[a][i] for a in AREAS]}
                          for i, g in enumerate(grados)]}
    t = tarjeta('grado', '¿Cambia entre 9°, 10° y 11°?', n, 10, metodo, conclusion, estado, grafica,
                ', '.join(f'{g}: {len(por[g])}' for g in grados) + ' estudiantes.',
                unidad='encuestas en el grado con menos')
    t['n_total'] = len(f)
    return t


# ─── H8. Colegios que faltan ──────────────────────────────────────────────── #

def h_cobertura(filas):
    metodo = {
        'pasos': ['La matrícula de 9°, 10° y 11° de cada sede viene de la capa de la Alcaldía de Medellín (2024).',
                  'Cobertura = estudiantes evaluados de la sede / su matrícula de 9° a 11°, con intervalo de Wilson.',
                  'El diagrama de Pareto ordena los colegios por encuestas y muestra cuántos concentran el 80 %.'],
        'formulas': [r'\text{cobertura}_s = \frac{\text{evaluados}_s}{m_{9,s} + m_{10,s} + m_{11,s}}',
                     r'\text{acumulado}_k = \frac{\sum_{j \le k} e_j}{\sum_j e_j}'],
        'supuestos': 'Solo las sedes de Medellín traen matrícula; las de otros municipios cuentan en el Pareto pero no en la cobertura.',
    }
    evaluados = Counter(x['colegio_codigo'] for x in filas if x['colegio_codigo'])
    n = sum(evaluados.values())
    if n < 1:
        return tarjeta('cobertura', '¿Qué colegios faltan?', 0, 1, metodo, unidad='estudiante con colegio')
    sedes = {s.codigo: s for s in SedeEducativa.query.all()}
    par = pr.pareto([(sedes[c].nombre_visible if c in sedes else c, v) for c, v in evaluados.items()])
    k80 = next(i + 1 for i, x in enumerate(par) if x['acumulado'] >= 0.8)
    con_matricula = [s for s in sedes.values() if s.matricula_media]
    sin_nadie = sorted([s for s in con_matricula if not evaluados.get(s.codigo)], key=lambda s: -s.matricula_media)
    oficiales_sin = sum(1 for s in sin_nadie if s.sector == 'Oficial')
    conclusion = (f'{k80} colegios concentran el 80 % de las encuestas. De las {len(con_matricula)} sedes de Medellín '
                  f'con 9° a 11°, {len(sin_nadie)} no tienen ningún estudiante evaluado ({oficiales_sin} oficiales).')
    metodo['resultado'] = f'{len(evaluados)} colegios con al menos un estudiante; {n} estudiantes con colegio.'
    grafica = {'tipo': 'pareto', 'etiquetas': [x['nombre'] for x in par[:15]], 'valores': [x['valor'] for x in par[:15]],
               'acumulado': [x['acumulado'] for x in par[:15]]}
    faltan = [{'nombre': s.nombre_visible, 'sector': s.sector, 'matricula': s.matricula_media,
               'comuna': s.comuna} for s in sin_nadie[:8]]
    t = tarjeta('cobertura', '¿Qué colegios faltan?', n, 1, metodo, conclusion, 'concluye', grafica,
                'Los de mayor matrícula sin evaluar, para empezar las visitas:', unidad='estudiante con colegio')
    t['lista'] = faltan
    return t


# ─── H10. Distancia casa-colegio ──────────────────────────────────────────── #

def h_distancia(filas):
    f = [x for x in filas if x['distancia_colegio_m'] is not None and x['sector'] in ('Oficial', 'Privado')]
    of = [x['distancia_colegio_m'] / 1000 for x in f if x['sector'] == 'Oficial']
    pv = [x['distancia_colegio_m'] / 1000 for x in f if x['sector'] == 'Privado']
    metodo = {
        'pasos': ['Se mide la distancia en línea recta entre la casa (ubicada a partir de la dirección) y la sede del colegio.',
                  'Se dibuja la función de distribución empírica (ECDF) de cada sector.',
                  'Se comparan las dos distribuciones con la prueba de Kolmogorov-Smirnov, que mira la mayor separación entre las curvas.'],
        'formulas': [r'd = 2R\arcsin\sqrt{\sin^2\tfrac{\Delta\varphi}{2} + \cos\varphi_1\cos\varphi_2\sin^2\tfrac{\Delta\lambda}{2}}',
                     r'D = \sup_x \left| F_{\text{of}}(x) - F_{\text{pr}}(x) \right|'],
        'supuestos': 'La distancia es en línea recta: caminando por calles suele ser cerca de 1,3 veces más.',
    }
    n = min(len(of), len(pv))
    if n < 15:
        return tarjeta('distancia', '¿Qué tan lejos viven de su colegio?', n, 15, metodo,
                       unidad='estudiantes con dirección en el sector con menos')
    ks = stats.ks_2samp(of, pv)
    m_of, m_pv = float(np.median(of)), float(np.median(pv))
    if ks.pvalue < ALFA:
        lejos = 'privados' if m_pv > m_of else 'oficiales'
        conclusion = (f'Los estudiantes de colegios {lejos} viven más lejos: la mitad está a más de '
                      f'{num(max(m_of, m_pv), 1)} km, frente a {num(min(m_of, m_pv), 1)} km en los otros.')
        estado = 'concluye'
    else:
        conclusion = (f'La distancia a su colegio es parecida en los dos sectores: la mitad vive a menos de '
                      f'{num(float(np.median(of + pv)), 1)} km.')
        estado = 'sin_evidencia'
    metodo['resultado'] = f'Medianas: oficiales {num(m_of, 2)} km, privados {num(m_pv, 2)} km. D = {num(ks.statistic)}, {valor_p(ks.pvalue)}.'
    grafica = {'tipo': 'ecdf', 'eje_x': 'Kilómetros de la casa al colegio', 'series': [
        {'nombre': f'Oficiales ({len(of)})', 'puntos': pr.ecdf(of)},
        {'nombre': f'Privados ({len(pv)})', 'puntos': pr.ecdf(pv)}]}
    t = tarjeta('distancia', '¿Qué tan lejos viven de su colegio?', n, 15, metodo, conclusion, estado, grafica,
                f'{len(of) + len(pv)} estudiantes con dirección y colegio del catálogo.',
                unidad='estudiantes con dirección en el sector con menos')
    t['n_total'] = len(of) + len(pv)
    return t


# ─── H11. Estabilidad al repetir ──────────────────────────────────────────── #

def h_estabilidad(filas):
    f = [x for x in filas if len(x['sesiones']) >= 2]
    n = len(f)
    metodo = {
        'pasos': ['Se toman los estudiantes que repitieron las dos pruebas en fechas distintas.',
                  'Se cuenta cuántos conservan el mismo perfil principal entre la primera y la última vez.',
                  'La proporción lleva su intervalo de Wilson al 95 %.'],
        'formulas': [r'\hat p = \frac{\#\{\,\text{primer perfil} = \text{último perfil}\,\}}{n}'],
        'supuestos': 'Entre una sesión y otra debe pasar tiempo; repetir el mismo día no cuenta.',
    }
    if n < 10:
        return tarjeta('estabilidad', '¿Cambia el perfil al repetir el test?', n, 10, metodo,
                       unidad='estudiantes que repitan el test')
    iguales = sum(1 for x in f if x['sesiones'][0] == x['sesiones'][-1])
    ic = pr.wilson(iguales, n)
    conclusion = f'{pct(ic["p"])} conserva su perfil principal al repetir el test.'
    metodo['resultado'] = f'{iguales} de {n}: {pct(ic["p"], 1)} [{pct(ic["bajo"], 1)} ; {pct(ic["alto"], 1)}].'
    grafica = {'tipo': 'barras', 'etiquetas': ['Lo conserva', 'Cambia'], 'valores': [iguales, n - iguales],
               'eje_y': 'Estudiantes'}
    return tarjeta('estabilidad', '¿Cambia el perfil al repetir el test?', n, 10, metodo, conclusion, 'concluye',
                   grafica, f'{n} estudiantes con dos sesiones o más.', unidad='estudiantes que repitan el test')


ORDEN = [h_cobertura, h_definicion, h_campos, h_gusto_habilidad, h_grado, h_sector, h_estrato, h_genero,
         h_municipio, h_distancia, h_estabilidad]


def todos(filas):
    return [h(filas) for h in ORDEN]
