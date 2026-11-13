"""Cohorte simulada del Valle de Aburrá para probar la estadística avanzada y el mapa.

Crea estudiantes ``simvalle<n>@simulacion.local`` (cohorte SIM-VALLE) que
responden las dos pruebas con el banco activo y tienen colegio, edad, género y
una dirección real. Todo queda marcado como simulado: los análisis lo excluyen
por defecto y lo muestran con un aviso cuando se incluye.

Supuestos, escritos también en el método de la página:
- El colegio se elige con probabilidad proporcional a su matrícula de 9° a 11°
  (cuando la fuente no la trae se usa la mediana de las que sí).
- El estudiante vive en una dirección real del índice a menos de 2,5 km de su
  colegio y en el mismo municipio.
- El gusto por cada campo RIASEC es aleatorio; las respuestas siguen ese gusto.

Se niega a correr si la base no es SQLite local.

Uso:
    python scripts/seeds/simular_cohorte_valle.py --cantidad 300
    python scripts/seeds/simular_cohorte_valle.py --borrar
"""

import argparse
import random
import sqlite3
import statistics
import sys
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / 'backend'))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models.aplicacion import Aplicacion, ConfiguracionAplicacion, Respuesta  # noqa: E402
from app.models.escolar import PerfilEscolar, SedeEducativa  # noqa: E402
from app.models.usuario import Consentimiento, Rol, Usuario  # noqa: E402
from app.services.auth_service import AuthService  # noqa: E402
from app.services.demografico_service import guardar_genero  # noqa: E402
from app.services.geo import geocodificador  # noqa: E402
from app.services.psicometrico_service import PsicometricoService  # noqa: E402

DOMINIO = '@simulacion.local'
PREFIJO = 'simvalle'
COHORTE = 'SIM-VALLE'
AREAS = ['Realista', 'Investigador', 'Artístico', 'Social', 'Emprendedor', 'Convencional']
RADIO_M = 2500


def direcciones_por_municipio():
    con = sqlite3.connect(geocodificador.ruta_indice())
    datos = {}
    for mpio, lat, lon, estrato, via, n1, l1, n2, l2, placa in con.execute(
            'SELECT municipio, lat, lon, estrato, via, n1, l1, n2, l2, placa FROM direcciones WHERE estrato IS NOT NULL'):
        datos.setdefault(mpio, []).append((lat, lon, estrato, f'{via} {n1}{(" " + l1) if l1 else ""} # {n2}{(" " + l2) if l2 else ""} - {placa}'))
    con.close()
    return datos


def casa_cerca(direcciones, sede, rnd):
    candidatas = direcciones.get(sede.municipio, [])
    dlat, dlon = RADIO_M / 111_000, RADIO_M / 110_500
    cerca = [d for d in candidatas if abs(d[0] - sede.lat) <= dlat and abs(d[1] - sede.lon) <= dlon
             and geocodificador.distancia_m(sede.lat, sede.lon, d[0], d[1]) <= RADIO_M]
    return rnd.choice(cerca) if cerca else None


def responder(aplicacion, gusto, rnd):
    inst = aplicacion.configuracion.instrumento
    items = [it for d in inst.dimensiones for e in d.escalas for it in e.items.filter_by(activo=True)]
    for it in items:
        ops = it.opciones or {}
        if it.tipo == 'comparacion_binaria':
            a, b = gusto[ops['opcion_a']['campo']], gusto[ops['opcion_b']['campo']]
            pa = a ** 2 / (a ** 2 + b ** 2)
            valor = 0 if rnd.random() < pa else 1
        else:
            g = gusto.get(it.escala.nombre, 0.5)
            opciones = ops.get('opciones', [])
            pesos = [(g * o['puntaje'] + (1 - g) * (5 - o['puntaje'])) ** 2 for o in opciones]
            valor = rnd.choices(range(len(opciones)), weights=pesos)[0]
        db.session.add(Respuesta(aplicacion_id=aplicacion.id, item_id=it.id, valor=valor,
                                 tiempo_respuesta_seg=rnd.randint(4, 25)))


def borrar():
    """Borra la cohorte y todo lo que cuelga de ella (SQLite no aplica los ON DELETE CASCADE)."""
    from app.models.demografico import DatoDemografico
    from app.models.resultado import PerfilVocacional, Reporte, ResultadoDimension
    ids = [u.id for u in Usuario.query.filter(Usuario.email.like(f'{PREFIJO}%{DOMINIO}')).all()]
    if not ids:
        return 0
    apps = [a.id for a in Aplicacion.query.filter(Aplicacion.usuario_id.in_(ids)).all()]
    perfiles = [p.id for p in PerfilVocacional.query.filter(PerfilVocacional.aplicacion_id.in_(apps)).all()]
    Reporte.query.filter(Reporte.perfil_id.in_(perfiles)).delete(synchronize_session=False)
    for modelo in (PerfilVocacional, ResultadoDimension, Respuesta):
        modelo.query.filter(modelo.aplicacion_id.in_(apps)).delete(synchronize_session=False)
    Aplicacion.query.filter(Aplicacion.id.in_(apps)).delete(synchronize_session=False)
    for modelo in (PerfilEscolar, DatoDemografico, Consentimiento):
        modelo.query.filter(modelo.usuario_id.in_(ids)).delete(synchronize_session=False)
    Usuario.query.filter(Usuario.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    return len(ids)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--cantidad', type=int, default=300)
    p.add_argument('--semilla', type=int, default=2026)
    p.add_argument('--borrar', action='store_true', help='Borra la cohorte simulada y termina')
    a = p.parse_args()

    app = create_app('development')
    with app.app_context():
        if 'sqlite' not in str(db.engine.url):
            sys.exit('Solo se corre contra la base SQLite local.')
        if a.borrar:
            print(f'{borrar()} estudiantes simulados borrados.')
            return
        if not geocodificador.hay_indice():
            sys.exit('Falta el índice de direcciones (scripts/geo/construir_indice_direcciones.py).')

        rnd = random.Random(a.semilla)
        rol = Rol.query.filter_by(nombre='estudiante').first()
        configs = sorted(ConfiguracionAplicacion.query.filter_by(activa=True).all(),
                         key=lambda c: 'Competencias' in c.instrumento.nombre)
        sedes = [s for s in SedeEducativa.query.all() if s.lat is not None]
        conocidas = [s.matricula_media for s in sedes if s.matricula_media]
        mediana = statistics.median(conocidas) if conocidas else 60
        pesos = [s.matricula_media or mediana for s in sedes]
        direcciones = direcciones_por_municipio()
        clave = AuthService.hash_password('Simulacion-no-entra-1*')
        ya = Usuario.query.filter(Usuario.email.like(f'{PREFIJO}%{DOMINIO}')).count()
        hoy = datetime.utcnow()

        creados = 0
        while creados < a.cantidad:
            sede = rnd.choices(sedes, weights=pesos)[0]
            casa = casa_cerca(direcciones, sede, rnd)
            if not casa:
                continue
            n = ya + creados + 1
            grado = rnd.choice([9, 10, 11])
            u = Usuario(email=f'{PREFIJO}{n}{DOMINIO}', password_hash=clave, nombres='Simulado',
                        apellidos=f'Valle {n}', rol_id=rol.id, semestre=grado, cohorte=COHORTE)
            db.session.add(u)
            db.session.flush()
            db.session.add(Consentimiento(usuario_id=u.id, texto_politica='Cohorte simulada.', aceptado=True))
            guardar_genero(u.id, rnd.choices(['Femenino', 'Masculino', 'Prefiero no decirlo'], weights=[48, 48, 4])[0])
            db.session.add(PerfilEscolar(
                usuario_id=u.id, sede_codigo=sede.codigo, sector=sede.sector,
                edad=grado + 5 + rnd.choice([-1, 0, 0, 0, 1]), municipio=sede.municipio,
                direccion=casa[3], direccion_normalizada=casa[3], lat=round(casa[0], 6), lon=round(casa[1], 6),
                precision='exacta', estrato=casa[2], simulado=True))

            gusto = {area: rnd.betavariate(2, 2) for area in AREAS}
            fin = hoy - timedelta(days=rnd.randint(0, 180), minutes=rnd.randint(0, 600))
            for cfg in configs:
                ap = Aplicacion(usuario_id=u.id, configuracion_id=cfg.id, estado='en_progreso',
                                fecha_inicio=fin - timedelta(minutes=20), user_agent='SimuladorCohorteValle/1.0')
                db.session.add(ap)
                db.session.flush()
                responder(ap, gusto, rnd)
                ap.estado, ap.progreso, ap.fecha_fin = 'completada', 100, fin
                db.session.commit()
                PsicometricoService.calcular_puntajes_dimension(ap.id)
                PsicometricoService.generar_perfil(ap.id)
                fin += timedelta(minutes=18)
            creados += 1
            if creados % 50 == 0:
                print(f'  {creados} de {a.cantidad}')
        print(f'Listo: {creados} estudiantes simulados en la cohorte {COHORTE}.')


if __name__ == '__main__':
    main()
