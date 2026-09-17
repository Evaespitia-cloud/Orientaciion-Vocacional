"""Regenera los perfiles vocacionales ya guardados.

El perfil se calcula una sola vez, cuando el estudiante termina la prueba, y
queda almacenado. Por eso, al corregir la fórmula, los perfiles anteriores
siguen mostrando los números viejos hasta que se vuelvan a generar.

Uso, desde la carpeta `backend` y con el entorno virtual activado:

    python ..\\scripts\\maintenance\\regenerar_perfiles.py           (solo muestra qué haría)
    python ..\\scripts\\maintenance\\regenerar_perfiles.py --aplicar (los regenera)

Regenerar no borra respuestas: recalcula el perfil a partir de las respuestas
que el estudiante ya dio.
"""

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "backend"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aplicar", action="store_true",
                        help="Guardar los cambios (sin esta opción solo se simula)")
    parser.add_argument("--aplicacion", type=int, default=None,
                        help="Regenerar solo una aplicación por su ID")
    args = parser.parse_args()

    from app import create_app
    from app.extensions import db
    from app.models.aplicacion import Aplicacion
    from app.services.psicometrico_service import PsicometricoService

    app = create_app()
    with app.app_context():
        consulta = Aplicacion.query.filter_by(estado="completada")
        if args.aplicacion:
            consulta = consulta.filter(Aplicacion.id == args.aplicacion)
        aplicaciones = consulta.order_by(Aplicacion.id).all()

        if not aplicaciones:
            print("No hay aplicaciones completadas para regenerar.")
            return 0

        print(f"Aplicaciones completadas encontradas: {len(aplicaciones)}")
        if not args.aplicar:
            print("MODO SIMULACIÓN — no se guardará nada. Agrega --aplicar para escribir.\n")

        ok = fallidas = 0
        for aplicacion in aplicaciones:
            try:
                perfil = PsicometricoService.generar_perfil(aplicacion.id)
                areas = (perfil.datos_json or {}).get("puntajes_por_area", {})
                fuera = [a for a, d in areas.items() if d.get("normalizado", 0) > 100]
                resumen = ", ".join(
                    f"{a}={d.get('normalizado')}%" for a, d in list(areas.items())[:3]
                )
                marca = "  *** SIGUE FUERA DE RANGO ***" if fuera else ""
                print(f"  Aplicación {aplicacion.id}: {perfil.perfil_principal} "
                      f"({resumen}…){marca}")
                ok += 1
            except Exception as exc:
                print(f"  Aplicación {aplicacion.id}: ERROR — {exc}")
                fallidas += 1

        if args.aplicar:
            db.session.commit()
            print(f"\nListo: {ok} perfiles regenerados, {fallidas} con error.")
        else:
            db.session.rollback()
            print(f"\nSimulación terminada: {ok} se regenerarían, {fallidas} fallarían.")
            print("Vuelve a ejecutarlo con --aplicar para guardarlo.")

        db.session.remove()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
