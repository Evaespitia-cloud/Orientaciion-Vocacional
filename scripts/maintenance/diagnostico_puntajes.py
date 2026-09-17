"""Diagnóstico de los porcentajes por área Holland.

Uso, desde la carpeta `backend`, con el entorno virtual activado:

    python ..\\scripts\\maintenance\\diagnostico_puntajes.py 1

donde 1 es el ID de la aplicación (el número que aparece al final de la URL
de resultados: /estudiante/resultados/1).

No modifica nada: solo lee y muestra en pantalla de dónde sale cada número.
"""

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "backend"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("aplicacion_id", type=int, help="ID de la aplicación a revisar")
    args = parser.parse_args()

    from app import create_app
    from app.extensions import db
    from app.models.aplicacion import Aplicacion
    from app.services.psicometrico_service import PsicometricoService

    app = create_app()
    with app.app_context():
        aplicacion = Aplicacion.query.get(args.aplicacion_id)
        if not aplicacion:
            print(f"No existe la aplicación {args.aplicacion_id}")
            return 1

        instrumento = aplicacion.configuracion.instrumento
        print("=" * 70)
        print(f"Aplicación {aplicacion.id} — instrumento: {instrumento.nombre}")
        print("=" * 70)

        # 1. Tipos de ítem: de aquí sale el tope de puntaje de cada uno
        print("\n1) TIPOS DE ÍTEM POR ESCALA")
        for dimension in instrumento.dimensiones:
            for escala in dimension.escalas:
                items = escala.items.filter_by(activo=True).all()
                if not items:
                    continue
                tipos = {}
                for it in items:
                    tipos[it.tipo] = tipos.get(it.tipo, 0) + 1
                topes = {
                    PsicometricoService._maximo_item(it) for it in items
                }
                print(f"   {dimension.nombre} / {escala.nombre}: "
                      f"{len(items)} ítems, tipos={tipos}, topes={sorted(topes)}")

        # 2. Puntajes por escala: bruto contra máximo
        print("\n2) PUNTAJES POR ESCALA (lo que alimenta el % por área)")
        escalas = PsicometricoService.calcular_puntajes_escala(aplicacion.id)
        for clave, d in sorted(escalas.items()):
            print(f"   {clave}")
            print(f"      bruto={d['puntaje_bruto']}  maximo={d['puntaje_maximo']}  "
                  f"items={d['total_items']}  respondidos={d['respondidos']}  "
                  f"-> normalizado={d['puntaje_normalizado']}%")
            if d['puntaje_maximo'] and d['puntaje_bruto'] > d['puntaje_maximo']:
                print("      *** El bruto supera al máximo: aquí está el desfase ***")

        # 3. Puntajes por dimensión (estos sí se veían bien en pantalla)
        print("\n3) PUNTAJES POR DIMENSIÓN")
        for r in PsicometricoService.calcular_puntajes_dimension(aplicacion.id):
            print(f"   {r.dimension.nombre}: bruto={r.puntaje_bruto} "
                  f"normalizado={r.puntaje_normalizado}% nivel={r.nivel}")

        # 4. Lo que quedó GUARDADO en el perfil, que es lo que pinta la página
        print("\n4) PERFIL GUARDADO (lo que muestra la tabla y el gráfico)")
        perfil = getattr(aplicacion, 'perfil', None)
        if perfil is None:
            from app.models.resultado import PerfilVocacional
            perfil = PerfilVocacional.query.filter_by(aplicacion_id=aplicacion.id).first()
        if not perfil:
            print("   (todavía no hay perfil generado)")
        else:
            print(f"   generado: {perfil.created_at}")
            areas = (perfil.datos_json or {}).get('puntajes_por_area', {})
            for area, d in areas.items():
                marca = "  <-- FUERA DE RANGO" if d.get('normalizado', 0) > 100 else ""
                print(f"   {area}: normalizado={d.get('normalizado')}% "
                      f"intereses={d.get('Intereses')} competencias={d.get('Competencias')}"
                      f"{marca}")

        print("\n" + "=" * 70)
        print("Si los valores del punto 2 están entre 0 y 100 pero los del punto 4")
        print("no, el perfil guardado quedó de una versión anterior del cálculo y")
        print("basta con regenerarlo. Si el punto 2 ya sale fuera de rango, el")
        print("problema está en el cálculo y hay que corregirlo.")
        print("=" * 70)

        db.session.remove()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
