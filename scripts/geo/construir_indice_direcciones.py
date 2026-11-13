"""Construye el índice local de direcciones del Valle de Aburrá.

Parte del archivo de medidores de energía (una fila por medidor con su dirección
y sus coordenadas en MAGNA-SIRGAS Origen Nacional, EPSG:9377) y deja una base
SQLite con una fila por dirección: la estructura normalizada, la latitud y la
longitud (promedio de los medidores de esa dirección) y el estrato más frecuente
de los medidores residenciales.

El índice no se versiona: los datos de origen no son públicos. Sin él, el
geocodificador usa OpenStreetMap y el pin manual.

Uso:
    python scripts/geo/construir_indice_direcciones.py --fuente RUTA/medidores_asignados.csv
    python scripts/geo/construir_indice_direcciones.py --fuente ... --salida backend/instance/direcciones_valle.sqlite

Requiere pandas y pyproj (no hacen falta en el servidor de la app).
"""

import argparse
import importlib.util
import os
import sqlite3
import time
from pathlib import Path

import pandas as pd
from pyproj import Transformer

RAIZ = Path(__file__).resolve().parents[2]

# Se carga el módulo por ruta para no arrastrar Flask con el paquete de la app.
_spec = importlib.util.spec_from_file_location('direcciones', RAIZ / 'backend/app/services/geo/direcciones.py')
_direcciones = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_direcciones)
normalizar, municipio_canonico = _direcciones.normalizar, _direcciones.municipio_canonico

SALIDA = RAIZ / 'backend' / 'instance' / 'direcciones_valle.sqlite'

ESQUEMA = """
CREATE TABLE direcciones (
    municipio TEXT NOT NULL,
    via TEXT NOT NULL, n1 INTEGER NOT NULL, l1 TEXT NOT NULL, bis1 INTEGER NOT NULL, s1 INTEGER NOT NULL,
    n2 INTEGER NOT NULL, l2 TEXT NOT NULL, bis2 INTEGER NOT NULL, s2 INTEGER NOT NULL,
    placa INTEGER NOT NULL,
    lat REAL NOT NULL, lon REAL NOT NULL,
    estrato INTEGER,
    medidores INTEGER NOT NULL,
    celda TEXT NOT NULL
);
CREATE INDEX ix_cuadra ON direcciones (municipio, via, n1, l1, bis1, s1, n2, l2, bis2, s2, placa);
CREATE INDEX ix_celda ON direcciones (celda);
CREATE TABLE metadatos (clave TEXT PRIMARY KEY, valor TEXT);
"""


def celda(lat, lon):
    """Rejilla de unos 110 m para buscar la dirección más cercana a un pin."""
    return f'{round(lat * 1000)}:{round(lon * 1000)}'


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--fuente', required=True, help='CSV con Direccion, Categoria, ESTRATO, N_Mpio, X, Y')
    p.add_argument('--salida', default=str(SALIDA))
    a = p.parse_args()

    t0 = time.time()
    df = pd.read_csv(a.fuente, usecols=['Direccion', 'Categoria', 'ESTRATO', 'N_Mpio', 'X', 'Y'],
                     dtype={'Direccion': str, 'Categoria': str, 'N_Mpio': str})
    total = len(df)
    df['municipio'] = df['N_Mpio'].map(municipio_canonico)
    df = df.dropna(subset=['municipio', 'X', 'Y'])

    unicas = df['Direccion'].dropna().unique()
    estructura = {d: normalizar(d) for d in unicas}
    df['dir'] = df['Direccion'].map(estructura)
    df = df.dropna(subset=['dir'])

    a_wgs84 = Transformer.from_crs('EPSG:9377', 'EPSG:4326', always_xy=True)
    lon, lat = a_wgs84.transform(df['X'].to_numpy(float), df['Y'].to_numpy(float))
    df['lat'], df['lon'] = lat, lon
    campos = ['via', 'n1', 'l1', 'bis1', 's1', 'n2', 'l2', 'bis2', 's2', 'placa']
    for c in campos:
        df[c] = df['dir'].map(lambda d, c=c: getattr(d, c))
    df['residencial'] = df['Categoria'].eq('RESIDENCIAL')
    df['ESTRATO'] = pd.to_numeric(df['ESTRATO'], errors='coerce')

    llave = ['municipio'] + campos
    grupos = df.groupby(llave, sort=False)
    salida = grupos.agg(lat=('lat', 'mean'), lon=('lon', 'mean'), medidores=('lat', 'size')).reset_index()
    estratos = (df[df['residencial'] & df['ESTRATO'].between(1, 6)]
                .groupby(llave, sort=False)['ESTRATO'].agg(lambda s: int(s.mode().iloc[0])))
    salida = salida.merge(estratos.rename('estrato').reset_index(), on=llave, how='left')
    for c in ('bis1', 's1', 'bis2', 's2'):
        salida[c] = salida[c].astype(int)
    salida['celda'] = [celda(la, lo) for la, lo in zip(salida['lat'], salida['lon'])]

    destino = Path(a.salida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        destino.unlink()
    con = sqlite3.connect(destino)
    con.executescript(ESQUEMA)
    columnas = llave + ['lat', 'lon', 'estrato', 'medidores', 'celda']
    con.executemany(f'INSERT INTO direcciones ({",".join(columnas)}) VALUES ({",".join("?" * len(columnas))})',
                    salida[columnas].astype(object).where(salida[columnas].notna(), None).itertuples(index=False, name=None))
    meta = {
        'fuente': os.path.basename(a.fuente),
        'medidores_leidos': total,
        'medidores_urbanos_con_direccion': len(df),
        'direcciones': len(salida),
        'construido': time.strftime('%Y-%m-%d %H:%M'),
    }
    con.executemany('INSERT INTO metadatos VALUES (?, ?)', [(k, str(v)) for k, v in meta.items()])
    con.commit()
    con.close()
    print(f'{len(salida):,} direcciones de {total:,} medidores en {time.time() - t0:.0f} s -> {destino}')
    print(salida.groupby('municipio').size().sort_values(ascending=False).to_string())


if __name__ == '__main__':
    main()
